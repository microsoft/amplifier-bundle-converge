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

# ---- deps -----------------------------------------------------------------
# amplifier_evaluation ships as a package inside the amplifier-bundle-
# evaluation repo, not as a published PyPI package this repo depends on
# directly. We resolve it the same way examples/*/run.sh in that repo do:
# prefer an already-activated venv, then fall back to a local checkout via
# PYTHONPATH if AMPLIFIER_EVALUATION_SRC is set, then fail loud with the
# exact remediation.
if ! python3 -c "import amplifier_evaluation" >/dev/null 2>&1; then
    if [ -n "${AMPLIFIER_EVALUATION_SRC:-}" ] && [ -d "$AMPLIFIER_EVALUATION_SRC/src" ]; then
        export PYTHONPATH="$AMPLIFIER_EVALUATION_SRC/src:${PYTHONPATH:-}"
    fi
fi
python3 -c "import amplifier_evaluation" >/dev/null 2>&1 || die \
    "amplifier_evaluation is not importable. Either activate its bundle venv \
first, or set AMPLIFIER_EVALUATION_SRC=/path/to/amplifier-bundle-evaluation \
(a checkout with 'uv sync' already run in it)."
python3 -c "import yaml" >/dev/null 2>&1 || die "PyYAML is not importable (needed by graders/programmatic.py)"

# ---- output dir -------------------------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$OUTPUT_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"
log "output: $OUTPUT_DIR"

# ---- run --------------------------------------------------------------
log "running harness.py $*"
python3 "$HERE/harness.py" --output "$OUTPUT_DIR" "$@"
HARNESS_EXIT=$?

log "harness exit: $HARNESS_EXIT"
log "results: $OUTPUT_DIR"
log "  - summary.json / run_meta.json          -- run-level results + provenance"
log "  - trials/<scenario>__trial-<n>/          -- per-trial state.json, rows, tracker items, sessions, grader/"
exit "$HARNESS_EXIT"
