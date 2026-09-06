"""Tests for scripts/install-check.py.

Every check is exercised twice — once in a faked environment where the thing is
present, once where it is absent — without touching the real machine. Fake
commands are small shell scripts written into a temporary directory that is put
at the front of PATH.

Run: pytest tests/test_install_check.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "install-check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("install_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules, so register first.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ic = _load_module()


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def fake_command(
    bin_dir: Path, name: str, rules: list[dict], default_rc: int = 3
) -> Path:
    """Write an executable stand-in for a real command.

    `rules` is a list of `{"match": <substring of the arguments>, "out": ...,
    "err": ..., "rc": ...}`; the first whose `match` appears in the joined
    arguments wins. `"match": "*"` matches anything. The stand-in is a Python
    script with an absolute interpreter, because these tests run with an empty
    PATH where even `/bin/sh` cannot find `cat`.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    payload = json.dumps({"rules": rules, "default_rc": default_rc})
    path.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        f"spec = json.loads({payload!r})\n"
        'args = " ".join(sys.argv[1:])\n'
        'for rule in spec["rules"]:\n'
        '    if rule["match"] == "*" or rule["match"] in args:\n'
        '        sys.stdout.write(rule.get("out", ""))\n'
        '        sys.stderr.write(rule.get("err", ""))\n'
        '        raise SystemExit(rule.get("rc", 0))\n'
        'raise SystemExit(spec["default_rc"])\n',
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


def always(out: str = "", rc: int = 0, err: str = "") -> list[dict]:
    """The simplest rule set: one answer, whatever the arguments."""
    return [{"match": "*", "out": out, "err": err, "rc": rc}]


@pytest.fixture
def empty_path(tmp_path, monkeypatch):
    """A PATH containing nothing but a directory we control."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))
    return bin_dir


@pytest.fixture
def ctx(tmp_path):
    return ic.Context(
        repo_root=tmp_path / "repo",
        amplifier_home=tmp_path / "amplifier-home",
        timeout=20.0,
    )


def make_repo(
    ctx,
    *,
    bundle_md: str | None = None,
    guard: bool = False,
    behavior: str | None = None,
):
    ctx.repo_root.mkdir(parents=True, exist_ok=True)
    if bundle_md is not None:
        (ctx.repo_root / "bundle.md").write_text(bundle_md, encoding="utf-8")
    if guard:
        pkg = (
            ctx.repo_root
            / "modules"
            / "hooks-candidate-guard"
            / "amplifier_module_hooks_candidate_guard"
        )
        pkg.mkdir(parents=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
    if behavior is not None:
        behaviours = ctx.repo_root / "behaviors"
        behaviours.mkdir(parents=True, exist_ok=True)
        (behaviours / "converge.yaml").write_text(behavior, encoding="utf-8")


ANCHORS_LINE = (
    "  - bundle: git+https://github.com/microsoft/amplifier-foundation"
    "@main#subdirectory=bundles/anchors/bundle.md\n"
)


def make_anchors_cache(ctx):
    target = (
        ctx.amplifier_home
        / "cache"
        / "amplifier-foundation-abc123"
        / "bundles"
        / "anchors"
    )
    target.mkdir(parents=True)
    (target / "bundle.md").write_text("# anchors\n", encoding="utf-8")


SKILL_LISTING = (
    "Result from load_skill:\n"
    "  {'message': 'Available Skills:\\n\\n**ten-lane-highway**: drive lanes\\n"
    "**goalify**: compose a goal\\n**goal-batch**: one batch\\n**monitor**: poll\\n'}"
)

GOAL_DOC = (
    "Result from read_file:\n  {'content': '# `/goal` — autonomous continuation'}"
)


def fake_amplifier(
    bin_dir: Path,
    *,
    skills: str = SKILL_LISTING,
    goal: str = GOAL_DOC,
    goal_rc: int = 0,
):
    """A stand-in `amplifier` that answers the two probes the check makes."""
    return fake_command(
        bin_dir,
        "amplifier",
        [
            {"match": "load_skill", "out": skills, "rc": 0},
            {"match": "GOAL_COMMAND", "out": goal, "rc": goal_rc},
        ],
    )


# --------------------------------------------------------------------------
# work queue command
# --------------------------------------------------------------------------


def test_work_queue_cli_ok(ctx, empty_path):
    fake_command(empty_path, "amplifier-work-tracker", always())
    result = ic.check_work_queue_cli(ctx)
    assert result.status == ic.OK


def test_work_queue_cli_missing(ctx, empty_path):
    result = ic.check_work_queue_cli(ctx)
    assert result.status == ic.MISSING
    assert "not on PATH" in result.detail


def test_work_queue_cli_missing_when_help_fails(ctx, empty_path):
    fake_command(empty_path, "amplifier-work-tracker", always(rc=7))
    result = ic.check_work_queue_cli(ctx)
    assert result.status == ic.MISSING
    assert "exited 7" in result.detail


# --------------------------------------------------------------------------
# work queue service
# --------------------------------------------------------------------------


SERVICE_ACTIVE = "platform: linux\ninstalled: True\nactive: True\n"
SERVICE_DOWN = "platform: linux\ninstalled: True\nactive: False\n"


def test_work_queue_service_ok_from_managed_service(ctx, empty_path):
    fake_command(empty_path, "amplifier-work-tracker", always(SERVICE_ACTIVE))
    result = ic.check_work_queue_service(ctx)
    assert result.status == ic.OK
    assert result.extra["managed_service_active"] is True


def test_work_queue_service_missing_when_inactive(ctx, empty_path):
    # Inactive managed unit AND no unmanaged server answering: that is MISSING.
    fake_command(
        empty_path,
        "amplifier-work-tracker",
        [
            {"match": "service", "out": SERVICE_DOWN, "rc": 0},
            {"match": "instances", "out": "connection refused\n", "rc": 1},
        ],
    )
    result = ic.check_work_queue_service(ctx)
    assert result.status == ic.MISSING
    assert "not active" in result.detail


def test_work_queue_service_ok_when_unmanaged_server_answers(ctx, empty_path):
    # Inactive managed unit but `instances` answers: reachable, unmanaged, OK —
    # the container case the turnkey run measured (systemd --user unavailable).
    fake_command(
        empty_path,
        "amplifier-work-tracker",
        [
            {"match": "service", "out": SERVICE_DOWN, "rc": 0},
            {"match": "instances", "out": "[]\n", "rc": 0},
        ],
    )
    result = ic.check_work_queue_service(ctx)
    assert result.status == ic.OK
    assert result.extra["reachable_unmanaged"] is True
    assert "unmanaged" in result.detail


def test_work_queue_service_ok_from_live_query(ctx, empty_path):
    ctx.project = "converge"
    fake_command(
        empty_path,
        "amplifier-work-tracker",
        [
            {"match": "service", "out": SERVICE_DOWN, "rc": 0},
            {"match": "status", "out": '{"project": "converge"}\n', "rc": 0},
        ],
    )
    result = ic.check_work_queue_service(ctx)
    assert result.status == ic.OK
    assert result.extra["live_query"] is True


def test_work_queue_service_missing_when_live_query_fails(ctx, empty_path):
    ctx.project = "converge"
    fake_command(
        empty_path,
        "amplifier-work-tracker",
        [
            {"match": "service", "out": SERVICE_ACTIVE, "rc": 0},
            {"match": "status", "err": "cannot reach server\n", "rc": 1},
        ],
    )
    result = ic.check_work_queue_service(ctx)
    assert result.status == ic.MISSING


def test_work_queue_service_skips_without_the_command(ctx, empty_path):
    result = ic.check_work_queue_service(ctx)
    assert result.status == ic.SKIP
    assert "not on PATH" in result.detail


# --------------------------------------------------------------------------
# parallel-lane helpers
# --------------------------------------------------------------------------


def test_lane_helpers_ok(ctx, empty_path):
    fake_amplifier(empty_path)
    result = ic.check_lane_helpers(ctx)
    assert result.status == ic.OK
    assert result.extra["helpers"] == {
        "ten-lane-highway": True,
        "goalify": True,
        "goal-batch": True,
        "monitor": True,
        "goal": True,
    }


def test_lane_helpers_ok_when_listing_is_line_wrapped(ctx, empty_path):
    """The real listing is wrapped for the terminal; a name must still match."""
    wrapped = SKILL_LISTING.replace("**monitor**", "**monitor**\n   ").replace(
        "**ten-lane-highway**", "\n**ten-lane-highway**"
    )
    fake_amplifier(empty_path, skills=wrapped)
    result = ic.check_lane_helpers(ctx)
    assert result.status == ic.OK


def test_lane_helpers_missing_one_skill(ctx, empty_path):
    fake_amplifier(
        empty_path, skills=SKILL_LISTING.replace("**monitor**", "**something-else**")
    )
    result = ic.check_lane_helpers(ctx)
    assert result.status == ic.MISSING
    assert "monitor" in result.detail
    assert result.extra["helpers"]["monitor"] is False


def test_lane_helpers_missing_goal_command(ctx, empty_path):
    fake_amplifier(empty_path, goal="not found", goal_rc=1)
    result = ic.check_lane_helpers(ctx)
    assert result.status == ic.MISSING
    assert "goal" in result.detail


def test_lane_helpers_skips_without_amplifier(ctx, empty_path):
    result = ic.check_lane_helpers(ctx)
    assert result.status == ic.SKIP
    assert "not on PATH" in result.detail


# --------------------------------------------------------------------------
# git worktrees
# --------------------------------------------------------------------------


def test_git_worktrees_ok_from_live_list(ctx, empty_path):
    ctx.repo_root.mkdir(parents=True)
    fake_command(empty_path, "git", always("/some/path abc123 [main]\n"))
    result = ic.check_git_worktrees(ctx)
    assert result.status == ic.OK
    assert "1 working copies" in result.detail


def test_git_worktrees_ok_from_version_when_not_a_repo(ctx, empty_path):
    ctx.repo_root.mkdir(parents=True)
    fake_command(
        empty_path,
        "git",
        [
            {"match": "worktree", "err": "fatal: not a git repository\n", "rc": 128},
            {"match": "--version", "out": "git version 2.43.0\n", "rc": 0},
        ],
    )
    result = ic.check_git_worktrees(ctx)
    assert result.status == ic.OK
    assert "2.43" in result.detail


def test_git_worktrees_missing_without_git(ctx, empty_path):
    result = ic.check_git_worktrees(ctx)
    assert result.status == ic.MISSING


def test_git_worktrees_missing_on_old_git(ctx, empty_path):
    ctx.repo_root.mkdir(parents=True)
    fake_command(
        empty_path,
        "git",
        [
            {"match": "worktree", "rc": 1},
            {"match": "--version", "out": "git version 2.1.0\n", "rc": 0},
        ],
    )
    result = ic.check_git_worktrees(ctx)
    assert result.status == ic.MISSING
    assert "2.5" in result.detail


# --------------------------------------------------------------------------
# tmux
# --------------------------------------------------------------------------


def test_tmux_ok(ctx, empty_path):
    fake_command(empty_path, "tmux", always("tmux 3.4\n"))
    result = ic.check_tmux(ctx)
    assert result.status == ic.OK
    assert "tmux 3.4" in result.detail


def test_tmux_missing(ctx, empty_path):
    result = ic.check_tmux(ctx)
    assert result.status == ic.MISSING


# --------------------------------------------------------------------------
# lean base
# --------------------------------------------------------------------------


def test_anchors_base_ok(ctx):
    make_repo(ctx, bundle_md="includes:\n" + ANCHORS_LINE)
    make_anchors_cache(ctx)
    result = ic.check_anchors_base(ctx)
    assert result.status == ic.OK


def test_anchors_base_missing_when_not_declared(ctx):
    make_repo(ctx, bundle_md="includes:\n  - bundle: something-else\n")
    make_anchors_cache(ctx)
    result = ic.check_anchors_base(ctx)
    assert result.status == ic.MISSING


def test_anchors_base_skips_when_declared_but_not_fetched(ctx):
    make_repo(ctx, bundle_md="includes:\n" + ANCHORS_LINE)
    result = ic.check_anchors_base(ctx)
    assert result.status == ic.SKIP
    assert "network" in result.detail


def test_anchors_base_skips_without_bundle_md(ctx):
    make_repo(ctx)
    result = ic.check_anchors_base(ctx)
    assert result.status == ic.SKIP


# --------------------------------------------------------------------------
# locked-contract guard
# --------------------------------------------------------------------------


def test_candidate_guard_ok(ctx):
    make_repo(ctx, guard=True, behavior="hooks:\n  - module: hooks-candidate-guard\n")
    result = ic.check_candidate_guard(ctx)
    assert result.status == ic.OK


def test_candidate_guard_missing_without_module(ctx):
    make_repo(ctx, behavior="hooks:\n  - module: hooks-candidate-guard\n")
    result = ic.check_candidate_guard(ctx)
    assert result.status == ic.MISSING


def test_candidate_guard_missing_when_not_wired_in(ctx):
    make_repo(ctx, guard=True, behavior="hooks: []\n")
    result = ic.check_candidate_guard(ctx)
    assert result.status == ic.MISSING
    assert "wire" in result.detail


# --------------------------------------------------------------------------
# the installed package is THIS tree
#
# Measured on 2026-09-06, adopter harness run 03:50Z, scenario 1: a worker lane
# ran `pip install -e` inside its own worktree, which binds the installed
# package to that worktree's path. The manager session merged to main, re-ran
# the check itself as Core 7 requires, and it passed -- through the stale
# binding, against the lane's tree rather than the merged one. The worktree was
# then removed and main was left with a broken install and a failing check.
# Every test below is that shape, in one direction or the other.
# --------------------------------------------------------------------------


def probe(**overrides) -> dict:
    """A reading from the installed command's own interpreter."""
    base = {
        "origin": None,
        "paths": [],
        "version": "0.1.0",
        "editable_source": None,
        "import_error": None,
        "dist_error": None,
        "command": "/usr/local/bin/amplifier-converge",
        "interpreter": "/usr/local/bin/python3",
    }
    base.update(overrides)
    return base


def in_tree(repo_root: Path) -> Path:
    """The package directory as an editable install of this repo resolves it."""
    package = repo_root / "src" / "amplifier_converge"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    return package


def test_installed_tree_ok_when_it_resolves_inside_this_repository(ctx):
    package = in_tree(ctx.repo_root)
    result = ic.judge_installed_tree(
        ctx.repo_root,
        probe(origin=str(package / "__init__.py"), editable_source=str(ctx.repo_root)),
    )
    assert result.status == ic.OK
    assert str(package) in result.detail


def test_installed_tree_missing_when_the_editable_source_was_removed(ctx, tmp_path):
    """The measured defect: a binding to a lane worktree that no longer exists."""
    gone = tmp_path / "lanes" / "w3-units" / "repo"
    result = ic.judge_installed_tree(
        ctx.repo_root,
        probe(editable_source=str(gone), import_error="no module named amplifier_converge"),
    )
    assert result.status == ic.MISSING
    assert str(gone) in result.detail
    assert "does not exist" in result.detail


def test_installed_tree_missing_when_the_package_directory_is_gone(ctx, tmp_path):
    """The same stale binding, seen through the import system instead."""
    gone = tmp_path / "lanes" / "w3-units" / "repo" / "src" / "amplifier_converge"
    result = ic.judge_installed_tree(
        ctx.repo_root, probe(origin=str(gone / "__init__.py"))
    )
    assert result.status == ic.MISSING
    assert str(gone) in result.detail
    assert "does not exist" in result.detail


def test_installed_tree_missing_when_it_resolves_to_another_working_copy(ctx, tmp_path):
    """A REAL path, and the wrong one: the quiet half of the measured defect.

    This is the reading that had to change. A check re-run through this binding
    runs the right command in the right repository and still measures another
    tree's code, which is exactly how a merge got certified against a lane.
    """
    ctx.repo_root.mkdir(parents=True, exist_ok=True)
    other = tmp_path / "lanes" / "w3-units" / "repo" / "src" / "amplifier_converge"
    other.mkdir(parents=True)
    (other / "__init__.py").write_text("", encoding="utf-8")
    result = ic.judge_installed_tree(
        ctx.repo_root, probe(origin=str(other / "__init__.py"))
    )
    assert result.status == ic.MISSING
    assert str(other) in result.detail
    assert str(ctx.repo_root) in result.detail


def test_installed_tree_missing_when_nothing_resolves_at_all(ctx):
    result = ic.judge_installed_tree(
        ctx.repo_root,
        probe(import_error="no module named amplifier_converge",
              dist_error="PackageNotFoundError('amplifier-converge')"),
    )
    assert result.status == ic.MISSING
    assert "neither import" in result.detail


def test_installed_tree_missing_when_the_source_is_there_but_will_not_import(ctx, tmp_path):
    source = tmp_path / "half-installed"
    source.mkdir()
    result = ic.judge_installed_tree(
        ctx.repo_root,
        probe(editable_source=str(source), import_error="ImportError('boom')"),
    )
    assert result.status == ic.MISSING
    assert "cannot import" in result.detail


def test_a_stale_binding_makes_the_whole_check_exit_one():
    """The recurrence guard: this cannot be a green run any more."""
    rows = [_row(ic.MISSING, ic.REQUIRED, ident="installed-tree")]
    assert ic.exit_code(rows) == 1


def test_the_checks_include_the_installed_tree():
    assert "installed-tree" in [check.ident for check in ic.CHECKS]


# --- the same thing end to end, through a fake command and interpreter ------


def fake_install(bin_dir: Path, report: dict) -> Path:
    """A console script whose shebang names an interpreter that answers `report`.

    Nothing here imports anything: the check reads the shebang of the installed
    command and asks THAT interpreter where the package is, which is the only
    way to ask about an install this script's own environment cannot see.
    """
    interpreter = fake_command(bin_dir, "fake-python", always(json.dumps(report)))
    script = bin_dir / "amplifier-converge"
    script.write_text(f"#!{interpreter}\n# console script\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_installed_tree_end_to_end_ok(ctx, empty_path):
    package = in_tree(ctx.repo_root)
    fake_install(empty_path, {"origin": str(package / "__init__.py"), "paths": [],
                              "version": "0.1.0", "editable_source": None,
                              "import_error": None, "dist_error": None})
    result = ic.check_installed_tree(ctx)
    assert result.status == ic.OK
    assert result.extra["interpreter"].endswith("fake-python")


def test_installed_tree_end_to_end_catches_the_removed_worktree(ctx, empty_path, tmp_path):
    gone = tmp_path / "lanes" / "w3-units" / "repo"
    fake_install(empty_path, {"origin": None, "paths": [], "version": "0.1.0",
                              "editable_source": str(gone),
                              "import_error": "no module named amplifier_converge",
                              "dist_error": None})
    result = ic.check_installed_tree(ctx)
    assert result.status == ic.MISSING
    assert str(gone) in result.detail


def test_installed_tree_skips_when_nothing_is_installed(ctx, empty_path):
    """No installed command is not a failing install; it is nothing to resolve."""
    result = ic.check_installed_tree(ctx)
    assert result.status == ic.SKIP
    assert "not on PATH" in result.detail


def test_installed_tree_missing_when_the_commands_interpreter_is_gone(ctx, empty_path, tmp_path):
    script = empty_path / "amplifier-converge"
    script.write_text(f"#!{tmp_path / 'removed-venv' / 'bin' / 'python'}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    result = ic.check_installed_tree(ctx)
    assert result.status == ic.MISSING
    assert "does not exist" in result.detail


def test_installed_tree_skips_when_the_interpreter_cannot_be_read(ctx, empty_path):
    script = empty_path / "amplifier-converge"
    script.write_text("no shebang here\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    result = ic.check_installed_tree(ctx)
    assert result.status == ic.SKIP
    assert "interpreter" in result.detail


def test_interpreter_of_reads_an_env_shebang(empty_path):
    fake_command(empty_path, "python3", always())
    script = empty_path / "amplifier-converge"
    script.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    found, how = ic.interpreter_of(script)
    assert found == str(empty_path / "python3")
    assert "PATH" in how


# --------------------------------------------------------------------------
# session history (optional)
# --------------------------------------------------------------------------


def test_session_history_ok(ctx):
    (ctx.amplifier_home / "cache" / "amplifier-bundle-context-intelligence-abc").mkdir(
        parents=True
    )
    result = ic.check_session_history(ctx)
    assert result.status == ic.OK


def test_session_history_missing(ctx):
    result = ic.check_session_history(ctx)
    assert result.status == ic.MISSING


# --------------------------------------------------------------------------
# every check has a degradation sentence
# --------------------------------------------------------------------------


def test_every_check_states_what_degrades():
    assert ic.CHECKS, "there must be checks to state anything about"
    for check in ic.CHECKS:
        sentence = check.degradation
        assert sentence, f"{check.ident} has no degradation sentence"
        assert sentence.startswith("Without "), (
            f"{check.ident} does not say what happens without it"
        )
        assert sentence.endswith("."), f"{check.ident}'s degradation is not a sentence"
        assert len(sentence.split()) >= 8, (
            f"{check.ident}'s degradation says too little"
        )


def test_every_check_carries_its_requirement_and_probe():
    for check in ic.CHECKS:
        assert check.requirement in (ic.REQUIRED, ic.OPTIONAL)
        assert check.probe
        assert check.name


def test_reported_rows_carry_the_degradation(ctx, empty_path):
    rows = ic.run_checks(ctx)
    assert len(rows) == len(ic.CHECKS)
    for row in rows:
        assert row["degradation"]
        assert row["status"] in (ic.OK, ic.MISSING, ic.SKIP)


# --------------------------------------------------------------------------
# never fabricates a pass
# --------------------------------------------------------------------------


def test_a_check_that_explodes_becomes_a_skip_not_a_pass(ctx):
    def boom(_ctx):
        raise RuntimeError("probe blew up")

    broken = ic.Check(
        ident="broken",
        name="Broken",
        requirement=ic.REQUIRED,
        degradation="Without this nothing at all works, which is why it matters.",
        probe="nothing",
        run=boom,
    )
    rows = ic.run_checks(ctx, [broken])
    assert rows[0]["status"] == ic.SKIP
    assert "probe blew up" in rows[0]["detail"]


def test_a_command_that_is_absent_is_never_reported_ok(ctx, empty_path):
    """With an empty PATH and an empty repo, nothing may claim to be present."""
    rows = ic.run_checks(ctx)
    assert all(row["status"] != ic.OK for row in rows), rows


# --------------------------------------------------------------------------
# exit code and output shape
# --------------------------------------------------------------------------


def _row(status, requirement=ic.REQUIRED, ident="x"):
    return {
        "id": ident,
        "name": "X",
        "requirement": requirement,
        "status": status,
        "detail": "d",
        "degradation": "Without it the thing does not work, which is the point.",
        "probe": "p",
    }


def test_exit_zero_when_nothing_required_is_missing():
    rows = [_row(ic.OK), _row(ic.MISSING, ic.OPTIONAL), _row(ic.SKIP)]
    assert ic.exit_code(rows) == 0


def test_exit_one_when_a_required_dependency_is_missing():
    rows = [_row(ic.OK), _row(ic.MISSING, ic.REQUIRED)]
    assert ic.exit_code(rows) == 1


def test_a_skip_never_makes_the_run_fail():
    assert ic.exit_code([_row(ic.SKIP, ic.REQUIRED)]) == 0


def test_table_names_the_degradation_for_anything_not_present(ctx):
    rows = [_row(ic.MISSING, ic.REQUIRED)]
    table = ic.render_table(rows, ctx)
    assert "Without it the thing does not work" in table
    assert "1 required dependency is missing." in table


def test_report_has_summary_and_checks(ctx):
    report = ic.build_report([_row(ic.OK)], ctx)
    assert report["summary"] == {
        "ok": 1,
        "missing": 0,
        "skipped": 0,
        "required_missing": 0,
    }
    assert report["checks"][0]["id"] == "x"
    assert report["contract"].startswith("operation.v1")


# --------------------------------------------------------------------------
# the command as a whole
# --------------------------------------------------------------------------


def _run_script(args, env_path):
    env = dict(os.environ)
    env["PATH"] = str(env_path)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )


def test_end_to_end_json_only_on_a_bare_machine(tmp_path, ctx):
    """An empty PATH and an empty repo: exit 1, JSON on stdout, nothing on stderr."""
    make_repo(ctx)
    bare = tmp_path / "bin"
    bare.mkdir()
    done = _run_script(
        [
            "--json-only",
            "--repo-root",
            str(ctx.repo_root),
            "--amplifier-home",
            str(ctx.amplifier_home),
            "--timeout",
            "20",
        ],
        bare,
    )
    assert done.returncode == 1
    assert done.stderr.strip() == ""
    report = json.loads(done.stdout)
    assert report["summary"]["required_missing"] > 0
    assert all(check["degradation"] for check in report["checks"])


def test_end_to_end_table_goes_to_stderr_and_json_to_stdout(tmp_path, ctx):
    make_repo(ctx)
    bare = tmp_path / "bin"
    bare.mkdir()
    done = _run_script(
        [
            "--repo-root",
            str(ctx.repo_root),
            "--amplifier-home",
            str(ctx.amplifier_home),
            "--timeout",
            "20",
        ],
        bare,
    )
    assert "Converge install check" in done.stderr
    json.loads(done.stdout)
