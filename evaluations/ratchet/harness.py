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
from amplifier_evaluation.harness.dtu import DTU, DTUError, cli_available

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
GRADING_FILE_REMOTE = f"{WORKSPACE}/_eval/reconcile_report.json"
PROJECTS_ROOT_REMOTE = "~/.amplifier/projects"


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
# JSON stdout parsing (tolerant of a banner line before the real payload,
# same defensive shape as harness/dtu.py's own envelope unwrapper)
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
) -> dict[str, Any]:
    """Invoke seed-reconcile non-interactively via `amplifier tool invoke`.

    Exact CLI shape settled on (verified against `amplifier tool invoke
    --help` and the recipe's own header-comment usage example):

        amplifier tool invoke recipes operation=execute \\
            recipe_path=@converge:recipes/seed-reconcile.yaml \\
            context='{"target_repo": "...", "tracker_project": "..."}' \\
            -o json

    `-o json` is the CLI's own documented flag for structured output; without
    it we would be parsing the human-readable text format, which is not a
    stable interface. Returns the parsed JSON tool-result envelope. Raises
    `TrialStepError` (never returns a partially-parsed result) on any
    non-zero exit or unparseable stdout.
    """
    context = {"target_repo": target_repo, "tracker_project": tracker_project}
    shell_cmd = (
        "amplifier tool invoke recipes "
        "operation=execute "
        f"recipe_path={RECIPE_PATH} "
        f"context={shlex.quote(json.dumps(context))} "
        "-o json"
    )
    result = await dtu.exec_cmd(
        ["bash", "-lc", shell_cmd], timeout_s=timeout_s, stream_to_logfile=log_path
    )
    if result.returncode != 0:
        raise TrialStepError(
            "running_agent",
            f"seed-reconcile invocation failed (exit {result.returncode}):\n"
            f"stdout(tail): {result.stdout[-3000:]}\nstderr(tail): {result.stderr[-3000:]}",
            exit_code=result.returncode,
        )
    payload = _parse_json_stdout(result.stdout)
    if payload is None:
        raise TrialStepError(
            "running_agent",
            "recipe invocation exited 0 but stdout was not parseable JSON "
            "(the `-o json` output shape may have changed since this harness "
            f"was written). First 2000 chars: {result.stdout[:2000]!r}",
        )
    return payload


async def _pull_rows(dtu: DTU, target_repo: str, host_dest: Path) -> bool:
    remote = f"{target_repo.rstrip('/')}/ledger/rows.yaml"
    check = await dtu.exec_cmd(
        ["bash", "-lc", f"test -f {shlex.quote(remote)}"], timeout_s=30
    )
    if check.returncode != 0:
        return False
    await dtu.file_pull(remote, host_dest)
    return True


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


async def _push_report_for_grading(dtu: DTU, report_payload: dict[str, Any]) -> None:
    """Write the last phase's recipe-result JSON to a known DTU path so the
    agent grader (bash + DTU exec only, no host filesystem access) can find
    it deterministically instead of hunting for it."""
    import tempfile

    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(report_payload, f, indent=2)
        tmp_path = Path(f.name)
    try:
        await dtu.exec_cmd(
            ["bash", "-lc", f"mkdir -p {shlex.quote(WORKSPACE + '/_eval')}"],
            timeout_s=30,
        )
        await dtu.file_push(tmp_path, GRADING_FILE_REMOTE)
    finally:
        tmp_path.unlink(missing_ok=True)


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
    scenario: Scenario, answer_key: dict[str, Any]
) -> str:
    """Task context handed to the agent grader -- includes the scenario
    description AND the recipe's own final-step spec text, inlined so the
    auditor (and anyone reading its `initial_report.md` afterward) has the
    exact bar it is grading against, not just a reference to it."""
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

The full report JSON is at {GRADING_FILE_REMOTE} inside this DTU. The
target repo (with its live ledger at `<target_repo>/ledger/rows.yaml`) is at
{TARGET_REPO}.
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
    tracker_project = (
        f"ratchet-{scenario.number}-t{trial_number}-{uuid.uuid4().hex[:6]}"
    )
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
        tracker_items_by_phase: dict[str, Path] = {}
        target_repo_by_phase: dict[str, Path] = {}
        last_report_payload: dict[str, Any] | None = None
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
            recipe_payload = await _exec_recipe(
                dtu,
                target_repo=TARGET_REPO,
                tracker_project=tracker_project,
                timeout_s=args.recipe_timeout,
                log_path=log_path,
            )
            (trial_dir / f"recipe-result-{phase}.json").write_text(
                json.dumps(recipe_payload, indent=2), encoding="utf-8"
            )
            last_report_payload = recipe_payload

            _stage(f"extracting:{phase}")
            rows_dest = trial_dir / f"rows-{phase}.yaml"
            if not await _pull_rows(dtu, TARGET_REPO, rows_dest):
                raise TrialStepError(
                    "extracting",
                    f"{TARGET_REPO}/ledger/rows.yaml not found after phase={phase!r}",
                )
            rows_by_phase[phase] = rows_dest

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
        _stage("grading:agent")
        assert last_report_payload is not None  # at least one phase always runs
        await _push_report_for_grading(dtu, last_report_payload)
        grader_dir = trial_dir / "grader"
        task_context = _build_agent_grader_task_context(scenario, answer_key)
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
            "python3": _host_cmd_version(["python3", "--version"]),
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
