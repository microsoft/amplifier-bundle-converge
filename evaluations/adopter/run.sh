#!/usr/bin/env bash
# Converge early-adopter eval -- thin entry point.
#
#   ./evaluations/adopter/run.sh                              # both scenarios
#   ./evaluations/adopter/run.sh --scenarios new-project      # just one
#   ./evaluations/adopter/run.sh --sync-mirror                # re-sync first
#   ./evaluations/adopter/run.sh --keep                       # leave the DTU up
#
# Every flag harness.py accepts passes straight through (`harness.py --help`).
#
# What this script adds over calling harness.py directly:
#
#   1. It resolves the INTERPRETER. `amplifier_evaluation` (the AI user, the
#      DTU brick) ships inside the amplifier-bundle-evaluation repo, not on
#      PyPI, and its AIUser composes an Amplifier bundle ON THE HOST -- which
#      installs dependencies into the running interpreter. A system python is
#      externally-managed and that install fails, so this refuses one and uses
#      that repo's own venv, exactly as ../ratchet/run.sh does.
#   2. It PROVES the Gitea mirror is current before anything launches. The
#      profile's url_rewrites points the README's install command at that
#      mirror; installing from a stale mirror would test yesterday's bundle and
#      report today's verdict. Default is CHECK and refuse with the fix --
#      `--sync-mirror` opts into the delete-and-recreate, because the mirror is
#      shared and an entry point should not silently destroy someone else's
#      fixture.
#   3. It resolves ANTHROPIC_API_KEY (the AI user AND the agent under test are
#      both real sessions) and GITEA_TOKEN from the environment or
#      ~/.amplifier/keys.env, minting a Gitea token if there is none. Never
#      echoed, never passed as a flag that would land in a process list.
#   4. It puts run output -- including the AI user's full transcript -- OUTSIDE
#      this repository. A transcript carries prompts and provider responses;
#      none of that belongs in a bundle's git history. Only RESULT.md, which
#      carries verdicts and probe output, is written into the tree.
#
# Prerequisites: python3, uv, git, amplifier-digital-twin, amplifier-gitea.
# It fails loud if one is missing rather than degrading into a run that cannot
# mean anything.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
WORKSPACE_ROOT="$(cd "$BUNDLE_ROOT/.." && pwd)"
OUTPUT_ROOT="$WORKSPACE_ROOT/.amplifier/evaluation/converge-adopter"

GITHUB_REPO="https://github.com/microsoft/amplifier-bundle-converge"
MIRROR_REPO="admin/amplifier-bundle-converge"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- where a launched container is registered -----------------------------
# A container is a MACHINE-WIDE resource, so its teardown row belongs in the
# machine-wide ledger the sweep actually reads -- not a lane-local file nobody
# opens. Prefer the outermost ancestor that already keeps an infra.tsv.
LEDGER_ROOT="${ADOPTER_LEDGER_ROOT:-}"
if [ -z "$LEDGER_ROOT" ]; then
    LEDGER_ROOT="$WORKSPACE_ROOT"
    probe="$WORKSPACE_ROOT"
    while [ "$probe" != "/" ] && [ "$probe" != "$HOME" ]; do
        [ -f "$probe/infra.tsv" ] && LEDGER_ROOT="$probe"
        probe="$(dirname "$probe")"
    done
fi

# ---- pass-through args, minus the ones this script consumes ---------------
SYNC_MIRROR=0
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --sync-mirror) SYNC_MIRROR=1 ;;
        *)             ARGS+=("$arg") ;;
    esac
done

# ---- preflight ------------------------------------------------------------
log "preflight"
for tool in python3 uv git amplifier-digital-twin amplifier-gitea; do
    command -v "$tool" >/dev/null || die "$tool is not on PATH"
done

if [ -f "$HOME/.amplifier/keys.env" ]; then
    set -a; . "$HOME/.amplifier/keys.env"; set +a
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY is not set and not in ~/.amplifier/keys.env. Both the AI user and the agent under test are real sessions; without a provider there is nothing to measure."

# ---- interpreter: the amplifier-evaluation venv ---------------------------
PY=""
if [ -n "${AMPLIFIER_EVALUATION_SRC:-}" ]; then
    [ -d "$AMPLIFIER_EVALUATION_SRC" ] || die "AMPLIFIER_EVALUATION_SRC=$AMPLIFIER_EVALUATION_SRC is not a directory"
    VENV_PY="$AMPLIFIER_EVALUATION_SRC/.venv/bin/python"
    if [ ! -x "$VENV_PY" ]; then
        log "no venv at $VENV_PY -- running 'uv sync' in $AMPLIFIER_EVALUATION_SRC"
        ( cd "$AMPLIFIER_EVALUATION_SRC" && uv sync ) || die "uv sync failed in $AMPLIFIER_EVALUATION_SRC"
    fi
    [ -x "$VENV_PY" ] || die "still no venv python at $VENV_PY after 'uv sync'"
    PY="$VENV_PY"
elif python3 -c "import amplifier_evaluation" >/dev/null 2>&1; then
    PY="$(command -v python3)"
    if ! python3 -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" >/dev/null 2>&1; then
        die "amplifier_evaluation is importable under a non-venv python ($PY), which is externally-managed: the AI user's on-host bundle-dependency install would fail there, before any DTU launches. Set AMPLIFIER_EVALUATION_SRC=/path/to/amplifier-bundle-evaluation and re-run."
    fi
else
    die "amplifier_evaluation not resolvable. Set AMPLIFIER_EVALUATION_SRC=/path/to/amplifier-bundle-evaluation (a checkout; 'uv sync' runs automatically if its .venv is missing)."
fi
"$PY" -c "from amplifier_evaluation.ai_user import AIUser" >/dev/null 2>&1 \
    || die "chosen interpreter $PY cannot import AIUser (broken venv? re-run 'uv sync' in \$AMPLIFIER_EVALUATION_SRC)"
log "interpreter: $PY"

# ---- the mirror the README's install command actually fetches -------------
GITEA_ID="${GITEA_ID:-$(amplifier-gitea list 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d[0]["id"] if d else "")')}"
[ -n "$GITEA_ID" ] || die "no Gitea environment exists. Create one: amplifier-gitea create"
GITEA_URL="${GITEA_URL:-$(amplifier-gitea list | python3 -c 'import sys,json;d=json.load(sys.stdin);print("http://localhost:%d" % d[0]["port"])')}"
if [ -z "${GITEA_TOKEN:-}" ]; then
    log "minting a Gitea token for $GITEA_ID"
    GITEA_TOKEN="$(amplifier-gitea token "$GITEA_ID" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')"
fi
[ -n "${GITEA_TOKEN:-}" ] || die "could not resolve a Gitea token"
export GITEA_URL GITEA_TOKEN

ORIGIN_SHA="$(git -C "$BUNDLE_ROOT" ls-remote "$GITHUB_REPO" refs/heads/main | cut -f1)"
[ -n "$ORIGIN_SHA" ] || die "could not read origin/main from $GITHUB_REPO"

mirror_sha() {
    curl -fsS "$GITEA_URL/api/v1/repos/$MIRROR_REPO/branches/main" 2>/dev/null \
        | python3 -c 'import sys,json;print(json.load(sys.stdin)["commit"]["id"])' 2>/dev/null || true
}
MIRROR_SHA="$(mirror_sha)"

if [ "$SYNC_MIRROR" = 1 ] && [ "$MIRROR_SHA" != "$ORIGIN_SHA" ]; then
    # `mirror-from-github` refuses (409) when the repo exists and the CLI has
    # no update verb, so re-syncing IS delete-and-recreate.
    log "re-syncing the mirror: ${MIRROR_SHA:-<absent>} -> $ORIGIN_SHA"
    curl -fsS -o /dev/null -X DELETE -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/repos/$MIRROR_REPO" || true
    amplifier-gitea mirror-from-github "$GITEA_ID" \
        --github-repo "$GITHUB_REPO" --no-issues --no-prs >/dev/null \
        || die "re-mirroring $GITHUB_REPO into $GITEA_ID failed"
    MIRROR_SHA="$(mirror_sha)"
fi

if [ "$MIRROR_SHA" != "$ORIGIN_SHA" ]; then
    log "mirror  $MIRROR_REPO main: ${MIRROR_SHA:-<absent>}"
    log "github  $GITHUB_REPO main: $ORIGIN_SHA"
    die "the mirror the README's install command resolves to is not current. Installing from it would test one commit and report a verdict about another. Re-run with --sync-mirror, or sync it yourself."
fi
log "mirror is current: $MIRROR_REPO main == github main ($ORIGIN_SHA)"

# ---- output, outside this repository --------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$OUTPUT_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"
log "output: $OUTPUT_DIR"
log "infra ledger: $LEDGER_ROOT/infra.tsv"

# ---- run ------------------------------------------------------------------
set +e
"$PY" "$HERE/harness.py" \
    --output "$OUTPUT_DIR" \
    --ledger-root "$LEDGER_ROOT" \
    "${ARGS[@]}" 2>&1 | tee "$OUTPUT_DIR/harness.log"
EXIT=${PIPESTATUS[0]}
set -e

log "harness exit: $EXIT"
log "RESULT.md:  $HERE/RESULT.md"
log "transcript: $OUTPUT_DIR/"
exit "$EXIT"
