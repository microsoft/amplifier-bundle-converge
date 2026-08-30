#!/usr/bin/env bash
# Converge ratchet eval -- thin entry point.
#
# Ensures deps, resolves an output directory OUTSIDE this repo (see below),
# and passes every argument straight through to harness.py.
#
# Usage:
#   ./run.sh --smoke                          # scenario 1, 1 trial, fast sanity check
#   ./run.sh                                   # full run: all 3 scenarios, 2 trials each
#   ./run.sh --scenarios 2 --trials 3          # just scenario 2, 3 trials
#   ./run.sh --profile /path/to/other.yaml     # override the DTU profile
#
# Any flag harness.py accepts (see `python harness.py --help`) can be passed
# through here unchanged.
#
# Output location (NEVER inside this repo -- run output can contain prompts,
# session traces, and provider responses, none of which belong in a bundle's
# git history):
#
#   /home/bkrabach/dev/vision-focused-team-ci/.amplifier/evaluation/converge-ratchet/<UTC-timestamp>/
#
# That path is under the WORKSPACE root's .amplifier/ directory, which is
# already gitignored (see the workspace root's .gitignore) -- confirmed
# before this script was written, not assumed.
#
# Prerequisites: amplifier-digital-twin, amplifier-work-tracker, python3, uv
# on PATH; ANTHROPIC_API_KEY set (or in ~/.amplifier/keys.env) for the agent
# grader's own Foundation session; a DTU profile (see README.md "Profile
# interface") and fixtures (see README.md "Fixtures interface") -- this
# script does NOT create either; it fails loud if they're missing, same as
# harness.py itself.
#
# CRITICAL -- INTERPRETER: harness.py must run under the amplifier-evaluation
# library's OWN uv venv, NOT the system python. The agent grader
# (Grader.setup) composes an Amplifier bundle ON THE HOST, and foundation's
# activator installs that bundle's deps into the RUNNING interpreter
# (`uv pip install -e ... --python <this-interpreter>`). System
# /usr/bin/python3 is externally-managed, so that install fails with exit 2
# before any DTU launches. The venv interpreter is writable, so the install
# lands in the venv's site-packages and setup() completes. This script
# therefore resolves and runs under "$AMPLIFIER_EVALUATION_SRC/.venv/bin/python".

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
WORKSPACE_ROOT="$(cd "$BUNDLE_ROOT/.." && pwd)"
OUTPUT_ROOT="$WORKSPACE_ROOT/.amplifier/evaluation/converge-ratchet"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- preflight ------------------------------------------------------------
log "preflight checks"
command -v python3 >/dev/null || die "python3 not on PATH"
command -v amplifier-digital-twin >/dev/null || die "amplifier-digital-twin not on PATH"

# Source ~/.amplifier/keys.env for any secret not already in the environment.
# Both ANTHROPIC_API_KEY and GITEA_TOKEN may live there.
if [ -f "$HOME/.amplifier/keys.env" ] &&
   { [ -z "${ANTHROPIC_API_KEY:-}" ] || [ -z "${GITEA_TOKEN:-}" ]; }; then
    set -a; . "$HOME/.amplifier/keys.env"; set +a
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env (needed by the agent grader's Foundation session)"
# GITEA_TOKEN authenticates the Gitea mirror the converge bundle installs
# from. Required, env-only, NEVER echoed here or written anywhere. harness.py
# also re-checks this and fails loud; we check early for a friendlier message.
[ -n "${GITEA_TOKEN:-}" ] || die "GITEA_TOKEN not set and not in ~/.amplifier/keys.env (required: the DTU profile's url_rewrites uses it to install the converge bundle from the Gitea mirror). Export it; never pass it as a flag."

# ---- resolve the interpreter (the amplifier-evaluation venv) --------------
# amplifier_evaluation ships as a package inside the amplifier-bundle-
# evaluation repo, not as a published PyPI package. We must run harness.py
# under THAT repo's uv venv (see the "CRITICAL -- INTERPRETER" note above),
# never system python. Resolution:
#   1. AMPLIFIER_EVALUATION_SRC set  -> use "$SRC/.venv/bin/python" (running
#      `uv sync` first if the venv is missing). This is the documented path.
#   2. Otherwise, if an already-ACTIVATED venv's python3 can import the
#      library, use it -- but refuse a system python (externally-managed;
#      the grader's dep install would fail there exactly as it did before).
PY=""
if [ -n "${AMPLIFIER_EVALUATION_SRC:-}" ]; then
    [ -d "$AMPLIFIER_EVALUATION_SRC" ] || die "AMPLIFIER_EVALUATION_SRC=$AMPLIFIER_EVALUATION_SRC is not a directory"
    VENV_PY="$AMPLIFIER_EVALUATION_SRC/.venv/bin/python"
    if [ ! -x "$VENV_PY" ]; then
        log "no venv at $VENV_PY -- running 'uv sync' in $AMPLIFIER_EVALUATION_SRC"
        command -v uv >/dev/null || die "uv not on PATH; cannot create the amplifier_evaluation venv. Install uv or pre-create the venv."
        ( cd "$AMPLIFIER_EVALUATION_SRC" && uv sync ) || die "uv sync failed in $AMPLIFIER_EVALUATION_SRC"
    fi
    [ -x "$VENV_PY" ] || die "still no venv python at $VENV_PY after 'uv sync'"
    PY="$VENV_PY"
elif python3 -c "import amplifier_evaluation" >/dev/null 2>&1; then
    PY="$(command -v python3)"
    # sys.prefix != sys.base_prefix means we're inside a venv (writable, safe
    # for the grader's dep install). A bare system python is NOT, and is the
    # exact failure this fix exists to prevent -- refuse it with the remedy.
    if ! python3 -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" >/dev/null 2>&1; then
        die "amplifier_evaluation is importable under a non-venv python ($PY), which is externally-managed: the agent grader's on-host bundle-dependency install would fail there (exit 2, before any DTU launches). Set AMPLIFIER_EVALUATION_SRC=/path/to/amplifier-bundle-evaluation and re-run, or activate that bundle's venv first."
    fi
else
    die "amplifier_evaluation not resolvable. Set AMPLIFIER_EVALUATION_SRC=/path/to/amplifier-bundle-evaluation (a checkout; 'uv sync' is run automatically if its .venv is missing), or activate that bundle's venv first."
fi

# Verify the chosen interpreter can actually import both deps we rely on.
"$PY" -c "import amplifier_evaluation" >/dev/null 2>&1 || die "chosen interpreter $PY cannot import amplifier_evaluation (a broken/incomplete venv? re-run 'uv sync' in \$AMPLIFIER_EVALUATION_SRC)"
"$PY" -c "import yaml" >/dev/null 2>&1 || die "chosen interpreter $PY cannot import PyYAML (needed by graders/programmatic.py)"
log "interpreter: $PY"

# ---- output dir -------------------------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$OUTPUT_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"
log "output: $OUTPUT_DIR"

# ---- run --------------------------------------------------------------
log "running harness.py $*"
"$PY" "$HERE/harness.py" --output "$OUTPUT_DIR" "$@"
HARNESS_EXIT=$?

log "harness exit: $HARNESS_EXIT"
log "results: $OUTPUT_DIR"
log "  - summary.json / run_meta.json          -- run-level results + provenance"
log "  - trials/<scenario>__trial-<n>/          -- per-trial state.json, rows, tracker items, sessions, grader/"
exit "$HARNESS_EXIT"
