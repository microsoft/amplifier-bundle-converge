#!/usr/bin/env python3
"""Converge early-adopter harness.

The question this answers -- and it is a different question from the one
`../turnkey/` answers:

    Can someone who has ONLY README.md, and no idea how any of this is built,
    get from a fresh machine to a project actually running the Converge way --
    on a NEW project, and on an EXISTING one?

Turnkey measures what a manager session does once it is running. This measures
everything BEFORE that: the install, finding the manager session at all, and
the first day of a project. Its profile therefore installs no Converge and no
work queue (see `profiles/adopter.yaml`'s header).

Shape of a run:

    launch a fresh DTU  ->  push README.md and the fixtures  ->  seed two
    repositories  ->  for each scenario, an AI USER who has read only that
    README drives the Amplifier CLI  ->  the harness JUDGES the container's
    own artifacts, never the AI user's account of them  ->  RESULT.md

The judging discipline, stated once: **the AI user's verdict is evidence about
the experience, never evidence about the artifacts.** Every PASS below comes
from a command this harness ran inside the container after the AI user
stopped, with the output pasted into RESULT.md. An AI user that says "I set up
the vision" and a container with no vision file on disk produce a FAIL.

Red is a real result. A first run where every step names what was missing is
worth more than a green one that assumed.
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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from amplifier_evaluation.ai_user import AIUser, InteractionResult
from amplifier_evaluation.harness.dtu import DTU, DTUError, cli_available

HERE = Path(__file__).resolve().parent
BUNDLE_ROOT = HERE.parent.parent

WORKSPACE = "/workspace"
README_IN_DTU = f"{WORKSPACE}/CONVERGE-README.md"

log = logging.getLogger("adopter")


# ---------------------------------------------------------------------------
# Step records
# ---------------------------------------------------------------------------

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


@dataclass
class Step:
    """One judged step. `evidence` is what was actually printed, verbatim."""

    id: str
    what: str
    verdict: str
    evidence: str
    missing: str = ""
    """When not PASS: what was absent, in plain words. Never empty on a FAIL --
    a red step that does not name what was missing is not a result."""

    def row(self) -> str:
        mark = {PASS: "PASS", FAIL: "FAIL", SKIP: "SKIP"}[self.verdict]
        detail = self.missing if self.verdict != PASS else _one_line(self.evidence)
        return f"| {self.id} | {self.what} | {mark} | {_escape(detail)} |"


@dataclass
class ScenarioRun:
    name: str
    project_dir: str
    steps: list[Step] = field(default_factory=list)
    interaction: InteractionResult | None = None
    ai_user_error: str = ""

    @property
    def verdict(self) -> str:
        if any(s.verdict == FAIL for s in self.steps):
            return FAIL
        if not self.steps or all(s.verdict == SKIP for s in self.steps):
            return SKIP
        return PASS


def _one_line(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "\u2026"


def _escape(text: str) -> str:
    return text.replace("|", "\\|")


def _fence(text: str, limit: int = 2000) -> str:
    body = text.strip()
    if len(body) > limit:
        body = body[:limit] + "\n\u2026 [truncated]"
    return "```\n" + (body or "(no output)") + "\n```"


# ---------------------------------------------------------------------------
# The infra ledger -- a container is machine-wide, so it is registered
# machine-wide, BEFORE it exists.
# ---------------------------------------------------------------------------

DEFAULT_LEDGER_SCRIPT = (
    Path.home()
    / ".local/share/uv/tools/amplifier/lib/python3.13/site-packages"
    / "amplifier_app_cli/data/skills/ten-lane-highway/scripts/infra_ledger.sh"
)


def register_infra(ledger_script: Path, ledger_root: Path, dtu_id: str) -> str:
    """Register the instance for teardown. Raises if the ledger is unreachable.

    An unregistered container that outlives the run is worse than a step the
    run could not perform, so this failing is fatal BEFORE anything launches.
    """
    if not ledger_script.exists():
        raise RuntimeError(f"infra ledger script not found: {ledger_script}")
    cmd = [
        str(ledger_script),
        str(ledger_root),
        "add",
        "dtu",
        dtu_id,
        f"amplifier-digital-twin destroy {dtu_id}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(
            f"infra ledger refused the registration (exit {proc.returncode}): "
            f"{proc.stderr.strip()}"
        )
    return " ".join(shlex.quote(c) for c in cmd)


# ---------------------------------------------------------------------------
# Probes -- every one of these runs INSIDE the container, after the AI user
# has stopped, and its raw output is the evidence.
# ---------------------------------------------------------------------------


async def probe(dtu: DTU, script: str, *, timeout_s: float = 120.0) -> tuple[int, str]:
    """Run a shell snippet in the container; return (rc, stdout+stderr)."""
    try:
        res = await dtu.exec_cmd(["bash", "-lc", script], timeout_s=timeout_s)
    except DTUError as exc:  # a probe that cannot run is a FAIL, never a PASS
        return 1, f"probe could not run: {exc}"
    out = res.stdout
    if res.stderr.strip():
        out = f"{out}\n[stderr] {res.stderr}"
    return res.returncode, out


async def judge_install(dtu: DTU, sid: str) -> Step:
    rc, out = await probe(
        dtu,
        "echo '--- bundle list ---'; amplifier bundle list 2>&1 | head -30; "
        "echo '--- agents list (converge rows) ---'; "
        "amplifier agents list 2>&1 | grep -i converge | head -10; true",
    )
    composed = "converge" in out.lower()
    agent_on = any(
        "[on]" in line and "converge" in line.lower() for line in out.splitlines()
    )
    if composed and agent_on:
        return Step(
            f"{sid}.1",
            "Converge installed and composed into the CLI",
            PASS,
            out,
        )
    return Step(
        f"{sid}.1",
        "Converge installed and composed into the CLI",
        FAIL,
        out,
        missing=(
            "no converge row in `amplifier bundle list`"
            if not composed
            else "converge is registered but no converge agent lists as [on] -- "
            "registered is not composed"
        ),
    )


async def judge_manager_session(dtu: DTU, sid: str, project_dir: str) -> Step:
    rc, out = await probe(
        dtu,
        "echo '--- tmux sessions ---'; tmux list-sessions 2>&1 | head -10; "
        "for L in '' '-L hw'; do tmux $L list-sessions 2>/dev/null | head -5; done; "
        "echo '--- agent pane, last 40 lines ---'; "
        "tmux capture-pane -p -t agent -S -40 2>&1 | tail -40; true",
    )
    has_session = "agent:" in out or "agent " in out
    in_mode = "[converge-manager]" in out
    if has_session and in_mode:
        return Step(
            f"{sid}.2",
            "A manager session is running against the project",
            PASS,
            out,
        )
    return Step(
        f"{sid}.2",
        "A manager session is running against the project",
        FAIL,
        out,
        missing=(
            "no live agent session at all"
            if not has_session
            else "a session is live but its prompt never shows `[converge-manager]` "
            "-- an ordinary session is not a manager session"
        ),
    )


async def judge_vision(dtu: DTU, sid: str, project_dir: str) -> Step:
    rc, out = await probe(
        dtu,
        f"cd {shlex.quote(project_dir)} 2>/dev/null || exit 1; "
        "find . -path ./.git -prune -o -iname 'VISION*.md' -print 2>/dev/null; "
        "echo '--- first 15 lines of each ---'; "
        "for f in $(find . -path ./.git -prune -o -iname 'VISION*.md' -print 2>/dev/null); "
        "do echo \"== $f\"; head -15 \"$f\"; done; true",
    )
    found = [ln for ln in out.splitlines() if ln.strip().endswith(".md") and "VISION" in ln.upper()]
    if found:
        return Step(f"{sid}.3", "A vision is written down in the project", PASS, out)
    return Step(
        f"{sid}.3",
        "A vision is written down in the project",
        FAIL,
        out,
        missing="no file matching VISION*.md anywhere in the project",
    )


async def judge_contract(dtu: DTU, sid: str, project_dir: str) -> Step:
    rc, out = await probe(
        dtu,
        f"cd {shlex.quote(project_dir)} 2>/dev/null || exit 1; "
        "ls -1 contracts/*.md 2>/dev/null; "
        "echo '--- headings ---'; "
        "head -1 contracts/*.md 2>/dev/null; true",
    )
    found = [ln for ln in out.splitlines() if ln.strip().startswith("contracts/")]
    if found:
        return Step(f"{sid}.4", "At least one contract is written down", PASS, out)
    return Step(
        f"{sid}.4",
        "At least one contract is written down",
        FAIL,
        out,
        missing="no contracts/*.md in the project",
    )


async def judge_ledger(dtu: DTU, sid: str, project_dir: str) -> Step:
    rc, out = await probe(
        dtu,
        f"cd {shlex.quote(project_dir)} 2>/dev/null || exit 1; "
        "find . -path ./.git -prune -o \\( -name 'rows.yaml' -o -path './ledger/*' \\) "
        "-print 2>/dev/null | head -20; "
        "echo '--- first 20 lines of ledger/rows.yaml ---'; "
        "head -20 ledger/rows.yaml 2>&1; true",
    )
    seeded = "ledger/rows.yaml" in out and "No such file" not in out
    if seeded:
        return Step(f"{sid}.5", "The project's contract check is seeded", PASS, out)
    return Step(
        f"{sid}.5",
        "The project's contract check is seeded",
        FAIL,
        out,
        missing="no ledger/rows.yaml (or equivalent contract check) in the project",
    )


async def judge_queue(dtu: DTU, sid: str) -> Step:
    rc, out = await probe(
        dtu,
        "if ! command -v amplifier-work-tracker >/dev/null; then "
        "  echo 'amplifier-work-tracker is not on PATH'; exit 3; fi; "
        "echo '--- instances ---'; amplifier-work-tracker instances 2>&1 | head -20; "
        "echo '--- items ---'; "
        "for p in $(amplifier-work-tracker instances 2>/dev/null "
        "  | tr -d '\"[],' | tr ' ' '\\n' | grep -v '^$' | head -5); do "
        "  echo \"== project $p\"; amplifier-work-tracker list --project \"$p\" 2>&1 | head -30; "
        "done; true",
        timeout_s=180.0,
    )
    if "is not on PATH" in out:
        return Step(
            f"{sid}.6",
            "A queue holds work that names the contracts it serves",
            FAIL,
            out,
            missing=(
                "the work queue CLI never arrived -- so no item, and no naming of "
                "any contract, can exist to be read"
            ),
        )
    names_contract = any(
        marker in out for marker in ("Contract:", "contract:", ".v1", "contracts/")
    )
    has_items = "==" in out and names_contract
    if has_items:
        return Step(
            f"{sid}.6", "A queue holds work that names the contracts it serves", PASS, out
        )
    return Step(
        f"{sid}.6",
        "A queue holds work that names the contracts it serves",
        FAIL,
        out,
        missing=(
            "the queue CLI is present but no item was found that names a contract"
        ),
    )


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


async def setup_container(dtu: DTU, readme: Path, out_dir: Path) -> list[Step]:
    """Push the README under test and the fixtures; seed both repositories."""
    steps: list[Step] = []

    await dtu.file_push(readme, README_IN_DTU)
    rc, out = await probe(dtu, f"wc -l {README_IN_DTU} && sha256sum {README_IN_DTU}")
    local_sha = subprocess.run(
        ["sha256sum", str(readme)], capture_output=True, text=True
    ).stdout.split()[0]
    if rc == 0 and local_sha in out:
        steps.append(
            Step(
                "G.2",
                "The README under test is in the container, byte for byte",
                PASS,
                out + f"\n[host] {local_sha}  {readme}",
            )
        )
    else:
        steps.append(
            Step(
                "G.2",
                "The README under test is in the container, byte for byte",
                FAIL,
                out + f"\n[host] {local_sha}  {readme}",
                missing="the pushed README's digest does not match the host's",
            )
        )

    await dtu.file_push(HERE / "fixtures", f"{WORKSPACE}/")
    rc, out = await probe(
        dtu,
        f"chmod +x {WORKSPACE}/fixtures/seed.sh && "
        f"{WORKSPACE}/fixtures/seed.sh new {WORKSPACE}/new-project && "
        f"{WORKSPACE}/fixtures/seed.sh existing {WORKSPACE}/existing-project && "
        f"echo '--- existing-project tests, as they stood before adoption ---' && "
        f"cd {WORKSPACE}/existing-project && (python3 -m pytest -q 2>&1 | tail -3)",
        timeout_s=300.0,
    )
    steps.append(
        Step(
            "G.3",
            "Both starting repositories are seeded and the existing one really works",
            PASS if rc == 0 else FAIL,
            out,
            missing="" if rc == 0 else f"seeding exited {rc}",
        )
    )
    return steps


async def run_scenario(
    dtu: DTU,
    ai_user: AIUser,
    name: str,
    sid: str,
    project_dir: str,
    scenario_path: Path,
    invocation: str,
    out_dir: Path,
    budget_s: float,
) -> ScenarioRun:
    run = ScenarioRun(name=name, project_dir=project_dir)
    scenario_text = scenario_path.read_text(encoding="utf-8")

    log.info("[%s] AI user starting (budget %.0fs)", name, budget_s)
    started = time.monotonic()
    try:
        run.interaction = await asyncio.wait_for(
            ai_user.run(
                scenario=scenario_text,
                dtu_id=dtu.id,
                invocation_guide=invocation,
                persona=(
                    "You are a pragmatic senior engineer adopting a new way of "
                    "working. You are comfortable at a terminal and you read "
                    "documentation carefully, but you have no prior knowledge of "
                    "this system and you refuse to guess at commands the "
                    "documentation does not give you -- when you cannot find "
                    "something, you say so plainly rather than inventing it. You "
                    "are the intent steward: you decide, and you do not ratify "
                    "anything you have not read."
                ),
                workspace_dir=project_dir,
            ),
            timeout=budget_s,
        )
    except asyncio.TimeoutError:
        run.ai_user_error = f"the AI user did not finish within {budget_s:.0f}s"
        log.warning("[%s] %s", name, run.ai_user_error)
    except Exception as exc:  # noqa: BLE001 -- recorded, never swallowed
        run.ai_user_error = f"{type(exc).__name__}: {exc}"
        log.warning("[%s] AI user failed: %s", name, run.ai_user_error)
    elapsed = time.monotonic() - started

    if run.interaction is not None:
        (out_dir / f"{sid}-ai-user.json").write_text(
            json.dumps(
                {
                    "scenario": name,
                    "elapsed_s": run.interaction.elapsed_s,
                    "session_id": run.interaction.ai_user_session_id,
                    "verdict": getattr(run.interaction.conclude, "verdict", None),
                    "summary": getattr(run.interaction.conclude, "summary", None),
                    "final_text": run.interaction.final_assistant_text,
                },
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
    log.info("[%s] AI user done in %.0fs; judging artifacts", name, elapsed)

    run.steps = [
        await judge_install(dtu, sid),
        await judge_manager_session(dtu, sid, project_dir),
        await judge_vision(dtu, sid, project_dir),
        await judge_contract(dtu, sid, project_dir),
        await judge_ledger(dtu, sid, project_dir),
        await judge_queue(dtu, sid),
    ]
    return run


def write_result(
    path: Path,
    *,
    global_steps: list[Step],
    scenarios: list[ScenarioRun],
    meta: dict,
) -> str:
    all_steps = list(global_steps) + [s for r in scenarios for s in r.steps]
    n_pass = sum(1 for s in all_steps if s.verdict == PASS)
    n_fail = sum(1 for s in all_steps if s.verdict == FAIL)
    n_skip = sum(1 for s in all_steps if s.verdict == SKIP)
    overall = "GREEN" if n_fail == 0 and n_pass else "RED"

    lines: list[str] = []
    lines.append("# Adopter harness — RESULT")
    lines.append("")
    lines.append(
        f"**{overall}** — {n_pass} pass · {n_fail} fail · {n_skip} skip, "
        f"run {meta['started']} on `{meta['dtu_id']}`."
    )
    lines.append("")
    lines.append(
        "What this run asked: can someone holding only `README.md` get a NEW "
        "project and an EXISTING project to the point of actually running the "
        "Converge way? Every verdict below was read out of the container by "
        "this harness AFTER the AI user stopped. The AI user's own account is "
        "reported separately, as evidence about the experience — never as "
        "evidence about the artifacts."
    )
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    for k in (
        "started",
        "finished",
        "dtu_id",
        "profile",
        "readme_sha256",
        "readme_matches_origin_main",
        "bundle_commit",
        "ledger_registration",
        "output_dir",
    ):
        if k in meta:
            lines.append(f"- **{k}** — `{meta[k]}`")
    lines.append("")

    lines.append("## Steps")
    lines.append("")
    lines.append("| # | What was asked | | What was missing (or, on a pass, what was seen) |")
    lines.append("|---|---|---|---|")
    for s in global_steps:
        lines.append(s.row())
    for run in scenarios:
        lines.append(f"| | **{run.name}** — `{run.project_dir}` | **{run.verdict}** | |")
        for s in run.steps:
            lines.append(s.row())
    lines.append("")

    lines.append("## What the AI user reported")
    lines.append("")
    lines.append(
        "The AI user read only `CONVERGE-README.md` and drove the Amplifier CLI "
        "as a person would. Where it says it could not find something, that is "
        "the finding this harness exists to surface."
    )
    lines.append("")
    for run in scenarios:
        lines.append(f"### {run.name}")
        lines.append("")
        if run.ai_user_error:
            lines.append(f"The AI user did not conclude: {run.ai_user_error}")
            lines.append("")
            continue
        inter = run.interaction
        if inter is None:
            lines.append("The AI user never ran.")
            lines.append("")
            continue
        verdict = getattr(inter.conclude, "verdict", None)
        summary = getattr(inter.conclude, "summary", None)
        lines.append(f"- **verdict** — `{verdict}` (after {inter.elapsed_s:.0f}s)")
        lines.append("")
        lines.append(_fence(summary or inter.final_assistant_text, limit=3000))
        lines.append("")

    lines.append("## Evidence, step by step")
    lines.append("")
    lines.append(
        "Verbatim output of the probe behind each row above. A probe that could "
        "not run is recorded as a failure, never as a pass."
    )
    lines.append("")
    for s in all_steps:
        lines.append(f"### {s.id} — {s.what} — {s.verdict}")
        lines.append("")
        if s.missing:
            lines.append(f"Missing: {s.missing}")
            lines.append("")
        lines.append(_fence(s.evidence))
        lines.append("")

    text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")
    return overall


async def amain(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.INFO, format="[%(asctime)s] %(levelname)s %(message)s"
    )
    logging.getLogger("amplifier_evaluation.harness.dtu").setLevel(logging.INFO)

    if not cli_available():
        log.error("amplifier-digital-twin is not on PATH")
        return 2

    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    readme = BUNDLE_ROOT / "README.md"
    if not readme.exists():
        log.error("README.md not found at %s", readme)
        return 2

    readme_sha = subprocess.run(
        ["sha256sum", str(readme)], capture_output=True, text=True
    ).stdout.split()[0]
    bundle_commit = subprocess.run(
        ["git", "-C", str(BUNDLE_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    origin_readme = subprocess.run(
        ["git", "-C", str(BUNDLE_ROOT), "show", "origin/main:README.md"],
        capture_output=True,
        text=True,
    )
    readme_matches_main = (
        "unknown"
        if origin_readme.returncode != 0
        else str(origin_readme.stdout == readme.read_text(encoding="utf-8"))
    )

    dtu_id = args.name or f"adopter-{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
    ledger_cmd = register_infra(
        Path(args.ledger_script), Path(args.ledger_root), dtu_id
    )
    log.info("registered in the infra ledger before launch: %s", ledger_cmd)

    meta = {
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dtu_id": dtu_id,
        "profile": str(args.profile),
        "readme_sha256": readme_sha,
        "readme_matches_origin_main": readme_matches_main,
        "bundle_commit": bundle_commit,
        "ledger_registration": ledger_cmd,
        "output_dir": str(out_dir),
    }

    variables = {}
    for key in ("GITEA_URL", "GITEA_TOKEN"):
        value = os.environ.get(key)
        if not value:
            log.error("%s is not set; the profile's url_rewrites needs it", key)
            return 2
        variables[key] = value

    global_steps: list[Step] = []
    scenarios: list[ScenarioRun] = []
    dtu: DTU | None = None
    try:
        log.info("launching %s from %s", dtu_id, args.profile)
        launch_started = time.monotonic()
        try:
            dtu = await DTU.launch(
                args.profile,
                name=dtu_id,
                variables=variables,
                launch_timeout_s=args.launch_timeout,
            )
            global_steps.append(
                Step(
                    "G.1",
                    "A fresh environment comes up with no Converge in it",
                    PASS,
                    f"launched {dtu.id} from {args.profile} in "
                    f"{time.monotonic() - launch_started:.0f}s; every readiness gate "
                    f"passed, including `converge-absent` and `queue-cli-absent`",
                )
            )
        except DTUError as exc:
            global_steps.append(
                Step(
                    "G.1",
                    "A fresh environment comes up with no Converge in it",
                    FAIL,
                    str(exc),
                    missing="the container never came up, so nothing after it could run",
                )
            )
            raise

        global_steps.extend(await setup_container(dtu, readme, out_dir))

        log.info("preparing the AI user (composes a foundation session; slow once)")
        ai_user = AIUser()
        await ai_user.setup()

        invocation = (HERE / "invocation.md").read_text(encoding="utf-8")
        wanted = {s.strip() for s in args.scenarios.split(",") if s.strip()}
        plan = [
            ("new-project", "S1", f"{WORKSPACE}/new-project", "New project"),
            (
                "existing-project",
                "S2",
                f"{WORKSPACE}/existing-project",
                "Existing project (adopt)",
            ),
        ]
        for key, sid, project_dir, label in plan:
            if wanted and key not in wanted:
                continue
            scenarios.append(
                await run_scenario(
                    dtu,
                    ai_user,
                    label,
                    sid,
                    project_dir,
                    HERE / "scenarios" / f"{key}.md",
                    invocation,
                    out_dir,
                    args.scenario_budget,
                )
            )
    except Exception as exc:  # noqa: BLE001 -- always write a RESULT
        log.error("run aborted: %s: %s", type(exc).__name__, exc)
    finally:
        meta["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if dtu is not None and not args.keep:
            log.info("destroying %s", dtu.id)
            try:
                await dtu.destroy()
                log.info("destroyed %s", dtu.id)
            except Exception as exc:  # noqa: BLE001
                log.error("DESTROY FAILED for %s: %s -- the ledger row is open, "
                          "sweep it", dtu.id, exc)
        elif dtu is not None:
            log.warning("--keep: %s left running; its ledger row is open", dtu.id)

    result_path = Path(args.result or (HERE / "RESULT.md"))
    overall = write_result(
        result_path, global_steps=global_steps, scenarios=scenarios, meta=meta
    )
    (out_dir / "report.json").write_text(
        json.dumps(
            {
                "meta": meta,
                "overall": overall,
                "steps": [
                    {
                        "id": s.id,
                        "what": s.what,
                        "verdict": s.verdict,
                        "missing": s.missing,
                    }
                    for s in list(global_steps)
                    + [s for r in scenarios for s in r.steps]
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    log.info("RESULT: %s -> %s", overall, result_path)
    return 0 if overall == "GREEN" else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, help="run output dir (OUTSIDE this repo)")
    p.add_argument("--result", default=None, help="path for RESULT.md")
    p.add_argument("--profile", default=str(HERE / "profiles" / "adopter.yaml"))
    p.add_argument("--name", default=None, help="explicit DTU instance name")
    p.add_argument("--scenarios", default="", help="comma list: new-project,existing-project")
    p.add_argument("--scenario-budget", type=float, default=2700.0)
    p.add_argument("--launch-timeout", type=float, default=1800.0)
    p.add_argument("--keep", action="store_true", help="do not destroy the DTU")
    p.add_argument("--ledger-root", default=str(BUNDLE_ROOT.parent))
    p.add_argument("--ledger-script", default=str(DEFAULT_LEDGER_SCRIPT))
    args = p.parse_args()
    return asyncio.run(amain(args))


if __name__ == "__main__":
    sys.exit(main())
