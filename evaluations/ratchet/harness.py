#!/usr/bin/env python3
"""Harness for the Converge "ratchet" evaluation.

Evaluates `converge:reconciler` + `recipes/seed-reconcile.yaml`: does the
ratchet actually make repo-vs-contract drift impossible to miss, without
spending owner attention? Three scenarios run against planted drumbeat-repo
fixtures (see README.md for the scenario table and the fixtures/profiles
interfaces this harness codes against).

This is a CUSTOM harness -- it does NOT use the stock `amplifier_evaluation`
`agents/<id>/` + `tasks/<id>/` benchmark convention, and does NOT use the
`AIUser` brick. Both are designed around driving an interactive agent CLI
conversationally; the system under test here is a specific, non-interactive
recipe invocation (`amplifier tool invoke recipes operation=execute ...`)
whose exact output shape and file locations are fully known to us up front.
Composing the low-level bricks directly (`DTU`, `Grader`) and doing our own
deterministic extraction (`dtu.exec_cmd` / `dtu.file_pull` against known
paths) is simpler, faster, and more reliable than routing through an
LLM-driven `Extractor` for artifacts whose location we already control. See
README.md "Design decisions" for the full rationale.

Per trial: launch a DTU from --profile -> seed the scenario via
fixtures/setup_scenario.sh -> for each phase (scenario 2 has two: "main" then
"drifted") run the seed-reconcile recipe non-interactively and extract its
artifacts (ledger rows, tracker items, a repo snapshot, and every session's
events.jsonl touched during that phase) -> run the programmatic (no-LLM)
checks -> run the agent grader for the judgment-requiring residue -> destroy
the DTU (unless --keep-on-failure and the trial failed).

Usage:
    python harness.py --profile profiles/ratchet.yaml --output <dir>
    python harness.py --smoke --profile profiles/ratchet.yaml --output <dir>

See `build_arg_parser()` / `--help` for the full flag set.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from amplifier_evaluation.grader import Grader
from amplifier_evaluation.grader.schema import GraderConfig
from amplifier_evaluation.harness.dtu import CommandResult, DTU, DTUError, cli_available

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graders import programmatic  # noqa: E402

logger = logging.getLogger("ratchet-eval")

HERE = Path(__file__).resolve().parent
BUNDLE_ROOT = (
    HERE.parent.parent
)  # evaluations/ratchet -> evaluations -> amplifier-bundle-converge
DEFAULT_FIXTURES_DIR = HERE / "fixtures"
DEFAULT_PROFILES_DIR = HERE / "profiles"
AGENT_GRADER_YAML = HERE / "graders" / "agent-grader.yaml"

RECIPE_PATH = "@converge:recipes/seed-reconcile.yaml"
WORKSPACE = "/workspace"
TARGET_REPO = f"{WORKSPACE}/target-repo"
# The SAME target repo expressed RELATIVE to the workspace root. The recipe is
# invoked with cwd=/workspace (see `_exec_recipe`), so it receives this
# workspace-relative path as its `target_repo` context var -- keeping the
# reconciler's writes inside tool-filesystem's default `allowed_write_paths`
# (["."] resolved from process cwd). This matches recipe v1.2's new default.
TARGET_REPO_REL = "./target-repo"
PROJECTS_ROOT_REMOTE = "~/.amplifier/projects"

# The reconcile deliverables the recipe writes into the target repo. `ledger/`
# is the recipe's own `ledger_dir` default (seed-reconcile.yaml context var,
# default "ledger/"); the harness does not override it, so these paths are
# fixed. The reconcile REPORT path is a v1.1.0+ recipe contract: the recipe is
# patched (in parallel) to write its reconcile report to
# `{{ledger_dir}}/reconcile-report.md` in the target repo. Trial success is
# judged by these ARTIFACTS existing after an exit-0 run -- NOT by parsing the
# recipe's stdout, which is a rendered session log (thinking blocks, tool
# panels, token usage), not a JSON envelope.
LEDGER_DIR_REMOTE = f"{TARGET_REPO}/ledger"
ROWS_REMOTE = f"{LEDGER_DIR_REMOTE}/rows.yaml"
RECONCILE_REPORT_REMOTE = f"{LEDGER_DIR_REMOTE}/reconcile-report.md"

# Post-run artifacts (basename -> remote path) that MUST exist after a
# successful reconcile. Both are required; a missing one after exit 0 is a
# structural trial failure naming exactly which artifact is absent.
REQUIRED_ARTIFACTS: dict[str, str] = {
    "ledger/rows.yaml": ROWS_REMOTE,
    "ledger/reconcile-report.md": RECONCILE_REPORT_REMOTE,
}

# The work-tracker service enforces this exact pattern on project names
# (verified live: `amplifier-work-tracker new ratchet-1-t1-4b1b4a` -> exit 1,
# "must match ^[a-z][a-z0-9_]{1,30}$"). Hyphens are REJECTED. This name is not
# just the harness's own `new`/`list` operand -- it is passed to the recipe as
# {{tracker_project}} and used by the reconciler's `work_add` inside the DTU,
# so an invalid name breaks any scenario that files GAP/VIOLATION items
# (scenarios 2 and 3 always do). Names must therefore use UNDERSCORES and cap
# at 31 chars total (1 leading letter + up to 30 of [a-z0-9_]).
_TRACKER_PROJECT_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
_TRACKER_PROJECT_MAXLEN = 31


def make_tracker_project(
    scenario: int, trial_number: int, rand: str | None = None
) -> str:
    """Generate a work-tracker project name valid under the service's
    ^[a-z][a-z0-9_]{1,30}$ constraint.

    Shape: ``ratchet_s<scenario>_t<trial>_<rand>`` (all underscores, never
    hyphens). `rand` defaults to 6 hex chars (all within [0-9a-f], so always
    valid). If the assembled name would exceed 31 chars (only reachable with
    absurdly large trial/scenario numbers), the random suffix is trimmed to
    fit rather than the identifying prefix. A defensive assertion guarantees
    the returned name matches the pattern before it is ever used -- as the
    `new` operand, as {{tracker_project}} for the recipe, and as the `list
    --project` operand at extraction.
    """
    if rand is None:
        rand = uuid.uuid4().hex[:6]
    prefix = f"ratchet_s{scenario}_t{trial_number}_"
    name = f"{prefix}{rand}"
    if len(name) > _TRACKER_PROJECT_MAXLEN:
        keep = max(1, _TRACKER_PROJECT_MAXLEN - len(prefix))
        name = f"{prefix}{rand[:keep]}"[:_TRACKER_PROJECT_MAXLEN]
    assert _TRACKER_PROJECT_RE.match(name), (
        f"generated tracker project name {name!r} does not match the "
        f"work-tracker service's required pattern ^[a-z][a-z0-9_]{{1,30}}$ "
        f"(scenario={scenario}, trial_number={trial_number})"
    )
    return name


# ---------------------------------------------------------------------------
# Scenario registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    number: int
    name: str
    phases: tuple[str, ...]  # git ref(s) the fixture repo is checked out to, in order
    description: str


SCENARIOS: dict[int, Scenario] = {
    1: Scenario(
        number=1,
        name="seed-clean",
        phases=("main",),
        description=(
            "First-population SEED run against a drumbeat fixture repo with frozen "
            "contracts and a planted mix of conforming and gap-worthy clauses. "
            "Measures basic detection fidelity: quote byte-match, clause coverage, "
            "and gap-to-tracker filing."
        ),
    ),
    2: Scenario(
        number=2,
        name="reconcile-drift",
        phases=("main", "drifted"),
        description=(
            "Two-phase: SEED on `main`, then RECONCILE again after `git checkout "
            "drifted` (a planted VIOLATION). Measures drift detection and "
            "idempotent re-run: rows updated in place by stable id, never "
            "renumbered or duplicated."
        ),
    ),
    3: Scenario(
        number=3,
        name="broken-kit-and-false-claim",
        phases=("main",),
        description=(
            "The repo's own conformance kit is broken/absent for some clauses, and "
            "a DONE.md falsely claims a clause is satisfied. Measures the "
            "'self-report is never proof' invariant (pillar 2) and zero "
            "owner-facing prompts."
        ),
    ),
}


class TrialStepError(RuntimeError):
    """A trial-stage failure that carries the stage name and, when known, the
    real process exit code -- so failures surface structurally instead of as
    an opaque string (see README 'Per-run capture')."""

    def __init__(
        self, stage: str, message: str, *, exit_code: int | None = None
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# JSON stdout parsing for the work-tracker `list --json` CLI ONLY.
#
# NOTE: this is deliberately NOT used for the seed-reconcile recipe. The
# recipe's stdout is a rendered session log, never JSON (see _exec_recipe).
# `amplifier-work-tracker list --json` IS a plain CLI that genuinely emits
# JSON, so parsing it here is correct. Tolerant of a banner line before the
# real payload, same defensive shape as harness/dtu.py's own envelope unwrapper.
# ---------------------------------------------------------------------------


def _parse_json_stdout(stdout: str) -> dict[str, Any] | None:
    s = stdout.strip()
    candidates = [s]
    if "\n" in s:
        last_line = s.rsplit("\n", 1)[-1].strip()
        if last_line:
            candidates.append(last_line)
        # Also try the largest brace-delimited span, in case of interleaved
        # log lines around the JSON payload.
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(s[start : end + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


# ---------------------------------------------------------------------------
# DTU operations specific to this eval (thin wrappers with clear failure
# messages; everything below composes `amplifier_evaluation.harness.dtu.DTU`)
# ---------------------------------------------------------------------------


async def _exec_recipe(
    dtu: DTU, *, target_repo: str, tracker_project: str, timeout_s: int, log_path: Path
) -> CommandResult:
    """Invoke seed-reconcile non-interactively via `amplifier tool invoke`.

    CLI shape (verified running against a live DTU):

        amplifier tool invoke recipes operation=execute \\
            recipe_path=@converge:recipes/seed-reconcile.yaml \\
            context='{"target_repo": "...", "tracker_project": "..."}'

    IMPORTANT -- stdout is a LOG, not structured output. An earlier version
    of this harness passed `-o json` and parsed stdout as a JSON tool-result
    envelope; a live smoke run proved that `-o json` streams the RENDERED
    SESSION output (thinking blocks, tool panels, token usage), not JSON, so
    stdout can never be parsed for control flow. We therefore drop `-o json`
    (its only purpose was the JSON we no longer parse) and treat stdout purely
    as diagnostics. Trial success is judged by exit code + post-run ARTIFACT
    existence (see `evaluate_recipe_outcome`), NOT by anything in stdout.

    IMPORTANT -- CWD = the workspace ROOT. The command is run as
    `cd /workspace && amplifier tool invoke ...`, and `target_repo` is passed
    as a path RELATIVE to that cwd (`./target-repo`). This is the owner-
    ratified "ephemeral workspaces live WITHIN cwd" design: tool-filesystem's
    default write policy is `allowed_write_paths=["."]`, and `"."` is resolved
    via `Path(".").resolve()` == the amplifier PROCESS cwd (proven in
    amplifier-module-tool-filesystem `write.py:38-39` + `path_validation.py`
    `is_in_path_list`). With cwd=/workspace, `/workspace` becomes a parent of
    `/workspace/target-repo/...`, so the reconciler's writes to the ledger /
    reconcile-report land inside the allowed tree -- no policy widening. The
    previous cwd left target-repo OUTSIDE `.`, causing Access-denied writes
    that trials laundered through bash heredocs (5) or honestly halted on (1).

    `target_repo` is expected to be a workspace-relative path (e.g.
    "./target-repo"); it is passed through verbatim as the recipe's
    `target_repo` context var (recipe v1.2's new default is "./target-repo",
    which we keep passing explicitly for older/newer recipe versions alike).

    Returns the raw `CommandResult` (exit code + stdout + stderr). The caller
    saves stdout verbatim and decides success; this function never raises on
    a non-zero exit, so the caller can attach the stdout/stderr tails to a
    single structural error.
    """
    context = {"target_repo": target_repo, "tracker_project": tracker_project}
    invoke = (
        "amplifier tool invoke recipes "
        "operation=execute "
        f"recipe_path={RECIPE_PATH} "
        f"context={shlex.quote(json.dumps(context))}"
    )
    # Run FROM the workspace root so tool-filesystem's default write policy
    # (allowed_write_paths=["."] -> Path(".").resolve() == process cwd) covers
    # the whole workspace, including the seeded target repo.
    shell_cmd = f"cd {shlex.quote(WORKSPACE)} && {invoke}"
    return await dtu.exec_cmd(
        ["bash", "-lc", shell_cmd], timeout_s=timeout_s, stream_to_logfile=log_path
    )


def evaluate_recipe_outcome(
    exit_code: int, artifacts_present: dict[str, bool]
) -> str | None:
    """Decide whether a reconcile run succeeded, from its exit code and which
    required artifacts exist afterward. PURE (no I/O) so it is unit-testable
    standalone.

    Success == exit 0 AND every required artifact present. Returns None on
    success, or a structural error message (naming the exact problem) on
    failure:
      - non-zero exit                -> "... exited nonzero (<code>)"
      - exit 0 but artifact(s) gone  -> "... but did not write: <names>"

    The second case is the whole point of judging by artifacts, not stdout:
    the recipe can exit 0 while its agent silently failed to produce the
    ledger or the reconcile report.
    """
    if exit_code != 0:
        return f"seed-reconcile invocation exited nonzero ({exit_code})"
    missing = sorted(name for name, present in artifacts_present.items() if not present)
    if missing:
        return (
            "seed-reconcile exited 0 but did not write required artifact(s): "
            + ", ".join(missing)
        )
    return None


async def _artifacts_present(dtu: DTU) -> dict[str, bool]:
    """Test-f each `REQUIRED_ARTIFACTS` path inside the DTU; return
    basename -> exists. Deterministic, no LLM."""
    present: dict[str, bool] = {}
    for name, remote in REQUIRED_ARTIFACTS.items():
        check = await dtu.exec_cmd(
            ["bash", "-lc", f"test -f {shlex.quote(remote)}"], timeout_s=30
        )
        present[name] = check.returncode == 0
    return present


async def _pull_tracker_items(dtu: DTU, tracker_project: str, host_dest: Path) -> None:
    """Pull the work-tracker item list for `tracker_project` via the
    OPERATOR-facing `amplifier-work-tracker list` CLI subcommand (distinct
    from the `work_list` agent tool -- see bundle.md's "Operator CLI surface"
    section) -- this is a deterministic, non-LLM extraction path.

    ASSUMPTION (not independently verified against a live DTU installation of
    the work-tracker service; the local host binary's `--help` output was
    used to confirm the flag shape, but the CLI's `--json` payload shape
    inside a fresh DTU was not exercised end-to-end): the command is
    `amplifier-work-tracker list --project <p> --limit 500 --json` and its
    JSON output is either a bare list or a dict with an `items` key.
    `graders.programmatic.load_tracker_items` tolerates both shapes.
    """
    cmd = f"amplifier-work-tracker list --project {shlex.quote(tracker_project)} --limit 500 --json"
    result = await dtu.exec_cmd(["bash", "-lc", cmd], timeout_s=60)
    if result.returncode != 0:
        raise TrialStepError(
            "extracting",
            f"amplifier-work-tracker list failed (exit {result.returncode}): "
            f"{result.stderr[-2000:]}",
            exit_code=result.returncode,
        )
    payload = _parse_json_stdout(result.stdout)
    text = json.dumps(payload) if payload is not None else result.stdout
    host_dest.write_text(text, encoding="utf-8")


async def _pull_optional_file(
    dtu: DTU, remote_path: str, host_dest: Path
) -> Path | None:
    check = await dtu.exec_cmd(
        ["bash", "-lc", f"test -f {shlex.quote(remote_path)}"], timeout_s=30
    )
    if check.returncode != 0:
        return None
    await dtu.file_pull(remote_path, host_dest)
    return host_dest


async def _touch_marker(dtu: DTU, marker: str) -> None:
    await dtu.exec_cmd(
        ["bash", "-lc", f"mkdir -p /tmp && touch {shlex.quote(marker)}"], timeout_s=30
    )


async def _find_new_session_dirs(dtu: DTU, marker: str) -> list[str]:
    """Find every session directory (recipe-session or a step's spawned
    sub-agent session) that wrote an events.jsonl since `marker` was touched.

    ASSUMPTION (documented, not independently verified): we do not attempt to
    resolve the exact parent-child linkage between the recipe-level session
    and each step's spawned sub-agent session (that linkage is an internal
    implementation detail of the recipes/coordinator machinery, not a
    documented interface). Instead we cast a net over the whole
    `~/.amplifier/projects` tree bounded by mtime, which captures every event
    stream this trial's recipe run actually produced -- sufficient for the
    'zero owner-facing prompts' scan, which only needs to see every event,
    not know which session it belongs to.
    """
    cmd = (
        f"find {PROJECTS_ROOT_REMOTE} -maxdepth 6 -type f -name events.jsonl "
        f"-newer {shlex.quote(marker)} 2>/dev/null | xargs -r -n1 dirname | sort -u"
    )
    result = await dtu.exec_cmd(["bash", "-lc", cmd], timeout_s=60)
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _collect_event_files(session_host_dirs: list[Path]) -> list[Path]:
    files: list[Path] = []
    for d in session_host_dirs:
        if not d.is_dir():
            continue
        files.extend(sorted(d.rglob("events.jsonl")))
    return files


def _token_totals(event_files: list[Path]) -> dict[str, int]:
    """Sum `llm:response` usage across every extracted events.jsonl for a
    trial -- the cheapest available proxy for per-trial cost, since neither
    the recipe tool result nor the `Grader` brick expose a token count
    directly. Malformed lines are skipped, not fatal (best-effort telemetry,
    not a correctness check)."""
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }
    for path in event_files:
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("event") != "llm:response":
                    continue
                usage = (ev.get("data") or {}).get("usage") or {}
                for key in totals:
                    totals[key] += int(usage.get(key, 0) or 0)
        except OSError:
            continue
    return totals


_AGENT_GRADER_CONFIG: GraderConfig | None = None


def _agent_grader_config() -> GraderConfig:
    """Parsed `agent-grader.yaml`, cached -- used only to re-embed each
    criterion's own points/description into the trial record (see
    `run_trial`'s "Inline the rubric text into the results" comment)."""
    global _AGENT_GRADER_CONFIG
    if _AGENT_GRADER_CONFIG is None:
        _AGENT_GRADER_CONFIG = GraderConfig.from_yaml(AGENT_GRADER_YAML)
    return _AGENT_GRADER_CONFIG


def _build_agent_grader_task_context(
    scenario: Scenario, answer_key: dict[str, Any], report_host_path: Path
) -> str:
    """Task context handed to the agent grader -- includes the scenario
    description AND the recipe's own final-step spec text, inlined so the
    auditor (and anyone reading its `initial_report.md` afterward) has the
    exact bar it is grading against, not just a reference to it.

    The report-quality input is the reconcile report the recipe wrote at
    `RECONCILE_REPORT_REMOTE` inside the DTU (a plain markdown file, NOT a
    JSON envelope -- the recipe streams a rendered session log to stdout, so
    the written artifact is the only reliable source). `report_host_path` is
    the host-extracted copy, referenced here for provenance only; the grader
    reads the live file in the DTU."""
    return f"""\
Scenario under test: converge ratchet eval, scenario {scenario.number} ({scenario.name}).
{scenario.description}

The agent under test was `converge:reconciler`, driven end-to-end by
`recipes/seed-reconcile.yaml` (non-interactively -- there was no human in the
loop for this run at all). Its final step's own specification for what the
reconcile report must contain is copied here verbatim so you can check
against it directly:

    EMIT THE RECONCILE REPORT as your final result:
      - rows tallied by disposition (CONFORMS / GAP / VIOLATION / OPEN-PINNED
        / NOT-ASSERTABLE / EXCLUDED / DIVERGED);
      - bidirectional drift found (each direction, or "none");
      - SYNC-row status ("current", or "re-review owed: <which contract hash
        changed>");
      - coverage-tripwire results (pass/fail for each of the three);
      - tracker items filed vs. already-open items referenced.
    Then STOP honestly -- if something could not be asserted or run, name it
    as a real residual rather than reporting a clean run that did nothing.

The reconcile report to grade is a markdown file at `{RECONCILE_REPORT_REMOTE}`
inside this DTU -- `cat` it. The target repo (with its live ledger at
`{ROWS_REMOTE}`) is at `{TARGET_REPO}`. (Host-archived copy of the report,
for provenance: `{report_host_path.name}`.)
"""


# ---------------------------------------------------------------------------
# Per-trial orchestration
# ---------------------------------------------------------------------------


async def run_trial(
    scenario: Scenario, trial_number: int, args: argparse.Namespace, grader: Grader
) -> dict[str, Any]:
    trial_id = f"scenario-{scenario.number}__trial-{trial_number}"
    trial_dir = args.output / "trials" / trial_id
    trial_dir.mkdir(parents=True, exist_ok=True)
    log_path = trial_dir / "trial.log"
    started = time.monotonic()

    record: dict[str, Any] = {
        "trial_id": trial_id,
        "scenario": scenario.number,
        "trial_number": trial_number,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "stages": [],
        "failures": [],
        "state": "running",
    }

    def _stage(name: str) -> None:
        record["stages"].append(
            {"stage": name, "at": datetime.now(timezone.utc).isoformat()}
        )
        logger.info("[%s] -> %s", trial_id, name)

    dtu: DTU | None = None
    tracker_project = make_tracker_project(scenario.number, trial_number)
    all_event_files: list[Path] = []

    try:
        # ---- launch ---------------------------------------------------
        _stage("launching")
        # Launch variables the profile's `url_rewrites` block is keyed on.
        # WITHOUT these, the DTU CLI SILENTLY skips proxy setup: the
        # ${GITEA_URL}/${GITEA_TOKEN} placeholders never resolve, the
        # converge `bundle add` falls through to real github.com, and the
        # install fails (verified by the DTU setup agent). GITEA_TOKEN comes
        # from the environment ONLY -- its presence is validated once in
        # `_main_async` preflight before any trial launches, so os.environ[]
        # here cannot KeyError in practice; it is a launch --var consumed by
        # the DTU's url_rewrites auth, never forwarded into the container env,
        # and never written to any harness file or log (the token-bearing
        # DTU-CLI debug line is suppressed in `_setup_logging`).
        launch_vars = {
            "GITEA_URL": args.gitea_url,
            "GITEA_TOKEN": os.environ["GITEA_TOKEN"],
        }
        dtu_name = f"ratchet-s{scenario.number}-t{trial_number}-{uuid.uuid4().hex[:6]}"
        try:
            dtu = await DTU.launch(args.profile, name=dtu_name, variables=launch_vars)
        except DTUError as exc:
            raise TrialStepError(
                "launching", str(exc), exit_code=exc.returncode
            ) from exc
        assert dtu is not None  # DTU.launch() either returns a DTU or raises
        record["dtu_id"] = dtu.id

        # ---- seed -------------------------------------------------------
        _stage("seeding")
        setup_script = args.fixtures_dir / "setup_scenario.sh"
        if not setup_script.is_file():
            raise TrialStepError(
                "seeding",
                f"expected fixtures setup script not found: {setup_script}. "
                "See README.md 'Fixtures interface'.",
            )
        answer_key_path = (
            args.fixtures_dir / "answer-key" / f"scenario-{scenario.number}.yaml"
        )
        answer_key = programmatic.load_answer_key(
            answer_key_path
        )  # fails loud on malformed fixture

        await dtu.exec_cmd(
            ["bash", "-lc", f"mkdir -p {shlex.quote(WORKSPACE)}"], timeout_s=30
        )
        await dtu.file_push(setup_script, "/tmp/setup_scenario.sh")
        gitea_arg = f" {shlex.quote(args.gitea_source)}" if args.gitea_source else ""
        seed_cmd = f"bash /tmp/setup_scenario.sh {scenario.number} {shlex.quote(TARGET_REPO)}{gitea_arg}"
        seed_result = await dtu.exec_cmd(
            ["bash", "-lc", seed_cmd], timeout_s=600, stream_to_logfile=log_path
        )
        if seed_result.returncode != 0:
            raise TrialStepError(
                "seeding",
                f"setup_scenario.sh failed (exit {seed_result.returncode}): {seed_result.stderr[-2000:]}",
                exit_code=seed_result.returncode,
            )

        # Pre-create the per-trial work-tracker project. The profile creates
        # projects with `amplifier-work-tracker new <name>` (its `dtu_warm`
        # smoke), and the reconciler files GAP/VIOLATION items into
        # `{{tracker_project}}` via `work_add`. Whether `work_add` auto-creates
        # a brand-new project or requires it to pre-exist is NOT clearly
        # documented (work_add's own text says "the sanctioned way to seed the
        # FIRST item(s) in a brand-new project" -- ambiguous). Creating it
        # first is strictly safe either way, so we do it defensively and treat
        # a failure as NON-fatal (if work_add turns out to auto-create, a
        # failed `new` here is harmless). The name is unique per trial, so it
        # can never collide with an existing project. Reported as an interface
        # assumption in README.
        create_proj = await dtu.exec_cmd(
            [
                "bash",
                "-lc",
                f"amplifier-work-tracker new {shlex.quote(tracker_project)}",
            ],
            timeout_s=60,
            stream_to_logfile=log_path,
        )
        if create_proj.returncode != 0:
            logger.warning(
                "[%s] `amplifier-work-tracker new %s` exited %s (non-fatal; "
                "proceeding on the assumption work_add can seed a brand-new "
                "project). stderr tail: %s",
                trial_id,
                tracker_project,
                create_proj.returncode,
                create_proj.stderr[-500:],
            )

        # ---- per-phase: run + extract ------------------------------------
        rows_by_phase: dict[str, Path] = {}
        report_by_phase: dict[str, Path] = {}
        tracker_items_by_phase: dict[str, Path] = {}
        target_repo_by_phase: dict[str, Path] = {}
        done_md_path: Path | None = None

        for phase in scenario.phases:
            if phase != scenario.phases[0]:
                _stage(f"seeding:checkout:{phase}")
                checkout = await dtu.exec_cmd(
                    [
                        "bash",
                        "-lc",
                        f"cd {shlex.quote(TARGET_REPO)} && git checkout {shlex.quote(phase)}",
                    ],
                    timeout_s=60,
                )
                if checkout.returncode != 0:
                    raise TrialStepError(
                        "seeding",
                        f"git checkout {phase} failed (exit {checkout.returncode}): {checkout.stderr[-1000:]}",
                        exit_code=checkout.returncode,
                    )

            marker = f"/tmp/{trial_id.replace('/', '-')}-{phase}.marker"
            await _touch_marker(dtu, marker)

            _stage(f"running_agent:{phase}")
            recipe_result = await _exec_recipe(
                dtu,
                target_repo=TARGET_REPO_REL,
                tracker_project=tracker_project,
                timeout_s=args.recipe_timeout,
                log_path=log_path,
            )
            # Save the recipe's stdout/stderr VERBATIM as diagnostics. It is a
            # rendered session log (thinking blocks, tool panels, token usage),
            # never structured output -- valuable to read, never parsed for
            # control flow.
            (trial_dir / f"recipe-stdout-{phase}.log").write_text(
                recipe_result.stdout, encoding="utf-8"
            )
            if recipe_result.stderr.strip():
                (trial_dir / f"recipe-stderr-{phase}.log").write_text(
                    recipe_result.stderr, encoding="utf-8"
                )

            # Success signal: exit 0 AND both post-run artifacts exist in the
            # target repo (ledger/rows.yaml AND ledger/reconcile-report.md).
            # The recipe can exit 0 while its agent silently failed to write a
            # deliverable -- that is a trial failure, named structurally.
            artifacts_present = await _artifacts_present(dtu)
            outcome_error = evaluate_recipe_outcome(
                recipe_result.returncode, artifacts_present
            )
            if outcome_error is not None:
                raise TrialStepError(
                    "running_agent",
                    f"{outcome_error}\n"
                    f"stdout(tail): {recipe_result.stdout[-3000:]}\n"
                    f"stderr(tail): {recipe_result.stderr[-3000:]}",
                    exit_code=recipe_result.returncode,
                )

            _stage(f"extracting:{phase}")
            # Artifact existence was just verified above, so these pulls should
            # not fail; keep defensive errors anyway.
            rows_dest = trial_dir / f"rows-{phase}.yaml"
            if await _pull_optional_file(dtu, ROWS_REMOTE, rows_dest) is None:
                raise TrialStepError(
                    "extracting",
                    f"{ROWS_REMOTE} not found after phase={phase!r} "
                    "(unexpected: it existed at the running_agent artifact check)",
                )
            rows_by_phase[phase] = rows_dest

            report_dest = trial_dir / f"reconcile-report-{phase}.md"
            if (
                await _pull_optional_file(dtu, RECONCILE_REPORT_REMOTE, report_dest)
                is None
            ):
                raise TrialStepError(
                    "extracting",
                    f"{RECONCILE_REPORT_REMOTE} not found after phase={phase!r} "
                    "(unexpected: it existed at the running_agent artifact check)",
                )
            report_by_phase[phase] = report_dest

            tracker_dest = trial_dir / f"tracker-items-{phase}.json"
            await _pull_tracker_items(dtu, tracker_project, tracker_dest)
            tracker_items_by_phase[phase] = tracker_dest

            repo_snapshot_dest = trial_dir / f"target-repo-{phase}"
            await dtu.file_pull(TARGET_REPO, repo_snapshot_dest)
            target_repo_by_phase[phase] = repo_snapshot_dest

            session_remote_dirs = await _find_new_session_dirs(dtu, marker)
            phase_session_dirs: list[Path] = []
            for i, remote_dir in enumerate(session_remote_dirs):
                dest = trial_dir / "sessions" / phase / f"s{i}"
                try:
                    await dtu.file_pull(remote_dir, dest)
                    phase_session_dirs.append(dest)
                except DTUError as exc:
                    logger.warning(
                        "[%s] could not pull session dir %s: %s",
                        trial_id,
                        remote_dir,
                        exc,
                    )
            all_event_files.extend(_collect_event_files(phase_session_dirs))

            if scenario.number == 3 and done_md_path is None:
                fc = answer_key.get("false_claim") or {}
                done_rel = fc.get("done_md_path", "DONE.md")
                done_md_path = await _pull_optional_file(
                    dtu, f"{TARGET_REPO.rstrip('/')}/{done_rel}", trial_dir / "DONE.md"
                )

        # ---- programmatic (no-LLM) grading -------------------------------
        _stage("grading:programmatic")
        prog_report = programmatic.run_all_checks(
            scenario=scenario.number,
            rows_by_phase=rows_by_phase,
            answer_key=answer_key,
            target_repo_by_phase=target_repo_by_phase,
            tracker_items_by_phase=tracker_items_by_phase,
            session_event_files=all_event_files,
            done_md_path=done_md_path,
        )
        (trial_dir / "programmatic_report.json").write_text(
            json.dumps(prog_report, indent=2), encoding="utf-8"
        )
        record["programmatic"] = {
            "passed": prog_report["passed"],
            "summary": prog_report["summary"],
        }

        # ---- agent grading (judgment residue) ----------------------------
        # The report-quality input is the reconcile-report.md the recipe wrote
        # (extracted per phase above). The grader runs against the live DTU and
        # reads it at its real, deterministic path RECONCILE_REPORT_REMOTE --
        # no push needed (the file already exists there); the host-extracted
        # copy under report_by_phase is the archived artifact.
        _stage("grading:agent")
        last_phase = scenario.phases[-1]
        grader_dir = trial_dir / "grader"
        task_context = _build_agent_grader_task_context(
            scenario, answer_key, report_by_phase[last_phase]
        )
        grader_result = await grader.run(
            grader_yaml_path=AGENT_GRADER_YAML,
            task_context=task_context,
            dtu_id=dtu.id,
            output_dir=grader_dir,
        )
        # "Inline the rubric text into the results" -- embed each criterion's
        # own points/description from agent-grader.yaml alongside its score,
        # so a reviewer never has to go dig up the grader.yaml separately.
        criteria_by_eval = {
            ev.name: ev.rubric_dict() for ev in _agent_grader_config().evaluations
        }
        record["agent_grader"] = {
            "overall_score": grader_result.overall_score,
            "evaluations": [
                {
                    "name": e.name,
                    "weight": e.weight,
                    "score": e.score,
                    "points_awarded": e.points_awarded,
                    "points_possible": e.points_possible,
                    "rubric": [
                        {
                            "criterion": k,
                            "points_possible": criteria_by_eval.get(e.name, {})
                            .get(k, {})
                            .get("points"),
                            "description": criteria_by_eval.get(e.name, {})
                            .get(k, {})
                            .get("description"),
                            "points_awarded": v.points_awarded,
                            "reasoning": v.reasoning,
                        }
                        for k, v in (e.rubric_scores or {}).items()
                    ],
                }
                for e in grader_result.evaluations
            ],
        }

        # ---- token telemetry ---------------------------------------------
        record["tokens"] = _token_totals(all_event_files)

        record["state"] = "completed"

    except TrialStepError as exc:
        record["failures"].append(
            {"stage": exc.stage, "message": str(exc), "exit_code": exc.exit_code}
        )
        record["state"] = "failed"
        logger.exception("[%s] FAILED at stage=%s", trial_id, exc.stage)
    except Exception as exc:  # noqa: BLE001 - trial-level containment; never propagates to the scheduler
        last_stage = record["stages"][-1]["stage"] if record["stages"] else "unknown"
        record["failures"].append(
            {
                "stage": last_stage,
                "message": f"{type(exc).__name__}: {exc}",
                "exit_code": None,
            }
        )
        record["state"] = "failed"
        logger.exception("[%s] FAILED (unhandled) at stage=%s", trial_id, last_stage)
    finally:
        _stage("cleaning_up")
        record["elapsed_s"] = time.monotonic() - started
        record["finished_at"] = datetime.now(timezone.utc).isoformat()
        if dtu is not None:
            if args.keep_on_failure and record["state"] == "failed":
                record["dtu_kept_for_debug"] = dtu.id
                logger.warning(
                    "[%s] --keep-on-failure: leaving DTU %s running for debugging "
                    "(destroy it yourself with `amplifier-digital-twin destroy %s`)",
                    trial_id,
                    dtu.id,
                    dtu.id,
                )
            else:
                await dtu.destroy()

    (trial_dir / "state.json").write_text(
        json.dumps(record, indent=2, default=str), encoding="utf-8"
    )
    return record


# ---------------------------------------------------------------------------
# Run-level orchestration
# ---------------------------------------------------------------------------


def _setup_logging(output_dir: Path, level: str) -> None:
    log_path = output_dir / "harness.log"
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(getattr(logging, level.upper(), logging.INFO))
    fh.setFormatter(fmt)
    root.addHandler(fh)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # SECRET-HYGIENE: the library's DTU CLI wrapper
    # (amplifier_evaluation.harness.dtu) logs the full launch argv -- which
    # includes `--var GITEA_TOKEN=<value>` -- at DEBUG level. Pin that one
    # logger to INFO so the token-bearing line is NEVER emitted, even when
    # this harness is run with `--log-level DEBUG`. Everything else from that
    # module (INFO "dtu launched", WARNING/ERROR) still flows through.
    logging.getLogger("amplifier_evaluation.harness.dtu").setLevel(logging.INFO)


def _host_cmd_version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, check=False
        )
        text = (out.stdout or out.stderr or "").strip()
        return text.splitlines()[0] if text else None
    except (OSError, subprocess.SubprocessError):
        return None


def _bundle_git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(BUNDLE_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _capture_run_meta(args: argparse.Namespace) -> dict[str, Any]:
    """Per-run capture: profile CONTENT (never just its path -- a profile can
    change or be deleted after the run), the converge bundle's git SHA at run
    time, and a best-effort host-side dependency inventory."""
    profile_text = (
        args.profile.read_text(encoding="utf-8") if args.profile.is_file() else None
    )
    return {
        "profile_path": str(args.profile),
        "profile_content": profile_text,
        "bundle_git_sha": _bundle_git_sha(),
        "host_dependency_inventory": {
            "amplifier-digital-twin": _host_cmd_version(
                ["amplifier-digital-twin", "--version"]
            ),
            "amplifier": _host_cmd_version(["amplifier", "--version"]),
            # The interpreter ACTUALLY running this harness (must be the
            # amplifier-evaluation venv, per run.sh -- recording sys.executable
            # here makes a wrong-interpreter run self-evident in run_meta.json,
            # rather than reporting whatever `python3` resolves to on PATH).
            "python": f"{sys.executable} ({sys.version.split()[0]})",
        },
    }


def _render_summary_text(summary: dict[str, Any]) -> str:
    lines = [
        f"ratchet eval run {summary['run_id']}",
        f"  trials: {summary['counts']}",
    ]
    for t in summary["trials"]:
        prog = t.get("programmatic", {})
        agent = t.get("agent_grader", {})
        lines.append(
            f"  {t['trial_id']:<40} state={t['state']:<10} "
            f"programmatic={'PASS' if prog.get('passed') else 'FAIL' if prog else '-'} "
            f"agent_score={agent.get('overall_score', '-')}"
        )
    return "\n".join(lines)


async def _main_async(args: argparse.Namespace) -> int:
    if not cli_available():
        raise RuntimeError(
            "`amplifier-digital-twin` CLI is not on PATH; install it before running."
        )
    if not args.profile.is_file():
        raise FileNotFoundError(
            f"DTU profile not found: {args.profile}\n"
            "This eval expects a profile providing: the amplifier CLI, the converge "
            "bundle installed from a Gitea mirror, a reachable work-tracker service, "
            "and provider API-key passthrough. See README.md 'Profile interface'."
        )
    if not args.fixtures_dir.is_dir():
        raise FileNotFoundError(
            f"fixtures dir not found: {args.fixtures_dir}\n"
            "Expected: fixtures/setup_scenario.sh and "
            "fixtures/answer-key/scenario-<n>.yaml. See README.md 'Fixtures interface'."
        )

    # GITEA_TOKEN is required and comes from the environment ONLY -- it is the
    # credential the profile's url_rewrites uses to authenticate against the
    # Gitea mirror when composing the converge bundle. Validate its presence
    # ONCE here, before any DTU launches, so the whole run fails loud and
    # early instead of every trial failing individually at launch. The token
    # value is never printed, written to a file, or logged (see the DTU-CLI
    # log suppression in `_setup_logging`).
    if not os.environ.get("GITEA_TOKEN"):
        raise RuntimeError(
            "GITEA_TOKEN is not set in the environment. It is required: the "
            "DTU profile's url_rewrites uses it to authenticate against the "
            "Gitea mirror when installing the converge bundle, and WITHOUT it "
            "the launch silently skips proxy setup and the bundle install "
            "falls through to real github.com and fails. Export GITEA_TOKEN "
            "(never pass it as a flag or write it to a file) and re-run."
        )

    args.output.mkdir(parents=True, exist_ok=True)
    _setup_logging(args.output, args.log_level)

    run_meta = _capture_run_meta(args)
    (args.output / "run_meta.json").write_text(
        json.dumps(run_meta, indent=2), encoding="utf-8"
    )

    scenario_numbers = [1] if args.smoke else args.scenarios
    trials_per_scenario = 1 if args.smoke else args.trials
    pairs = [
        (SCENARIOS[n], t)
        for n in scenario_numbers
        for t in range(1, trials_per_scenario + 1)
    ]

    logger.info("preparing agent grader (expensive bundle setup, once)...")
    grader = Grader()
    await grader.setup()

    sem = asyncio.Semaphore(args.max_parallel)

    async def _bounded(scenario: Scenario, trial_number: int) -> dict[str, Any]:
        async with sem:
            return await run_trial(scenario, trial_number, args, grader)

    started_at = datetime.now(timezone.utc).isoformat()
    logger.info("starting %d trial(s), max_parallel=%d", len(pairs), args.max_parallel)
    results = list(await asyncio.gather(*(_bounded(s, t) for s, t in pairs)))
    finished_at = datetime.now(timezone.utc).isoformat()

    counts: dict[str, int] = {}
    for r in results:
        counts[r["state"]] = counts.get(r["state"], 0) + 1

    summary = {
        "run_id": args.output.name,
        "started_at": started_at,
        "finished_at": finished_at,
        "counts": counts,
        "trials": results,
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    print(_render_summary_text(summary))
    logger.info("results: %s", args.output)

    return 1 if any(r["state"] != "completed" for r in results) else 0


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILES_DIR / "ratchet.yaml",
        help="DTU profile to launch from (default: profiles/ratchet.yaml under this eval dir)",
    )
    ap.add_argument("--fixtures-dir", type=Path, default=DEFAULT_FIXTURES_DIR)
    ap.add_argument("--output", type=Path, required=True, help="run output directory")
    ap.add_argument(
        "--scenarios",
        type=int,
        nargs="*",
        default=[1, 2, 3],
        choices=[1, 2, 3],
        help="which scenarios to run",
    )
    ap.add_argument(
        "--trials", type=int, default=2, help="trials per scenario (default: 2)"
    )
    ap.add_argument(
        "--max-parallel", type=int, default=3, help="max concurrent DTUs (default: 3)"
    )
    ap.add_argument(
        "--smoke",
        action="store_true",
        help="scenario 1 only, 1 trial -- overrides --scenarios/--trials",
    )
    ap.add_argument(
        "--keep-on-failure",
        action="store_true",
        help="do not destroy a trial's DTU if the trial fails (leaves it running for debugging)",
    )
    ap.add_argument(
        "--recipe-timeout",
        type=int,
        default=3600,
        help="per-invocation timeout for the seed-reconcile recipe, in seconds (default: 3600)",
    )
    ap.add_argument(
        "--gitea-url",
        default="http://10.119.176.1:10230",
        help=(
            "Gitea mirror URL reachable FROM INSIDE the DTU, passed as the "
            "${GITEA_URL} launch --var the profile's url_rewrites resolves. "
            "Default is the Incus bridge gateway (a stable DTU->host route, "
            "verified by the DTU setup agent)."
        ),
    )
    ap.add_argument(
        "--gitea-source",
        default="http://10.119.176.1:10230/admin/drumbeat.git",
        help=(
            "Source repo forwarded as the 3rd arg to fixtures/setup_scenario.sh "
            "(where the drumbeat fixture is cloned from INSIDE the DTU). "
            "Default is the Gitea drumbeat mirror -- REQUIRED for seeding: the "
            "fixture script's own default is a host path that does not exist "
            "in the container."
        ),
    )
    ap.add_argument("--log-level", default="INFO")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        return asyncio.run(_main_async(args))
    except (RuntimeError, FileNotFoundError) as exc:
        print(f"FAIL LOUD: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
