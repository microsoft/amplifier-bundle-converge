#!/usr/bin/env bash
# Converge turnkey eval -- thin entry point.
#
#   ./evaluations/turnkey/run.sh                      # driven: fresh DTU, real wave
#   ./evaluations/turnkey/run.sh --sync-mirror        # re-sync the mirror first
#   ./evaluations/turnkey/run.sh --no-wave            # stand it up, judge, no wave
#   ./evaluations/turnkey/run.sh --env local --workspace ~/dev/hw-converge
#   ./evaluations/turnkey/run.sh --self-check
#
# Every flag run.py accepts passes straight through (see `run.py --help`).
#
# What this script adds over calling run.py directly, and why each piece is
# here rather than in the harness:
#
#   1. It PROVES the Gitea mirror the DTU profile installs from is current
#      before anything launches. The profile's url_rewrites points the one
#      documented install at that mirror; installing from a stale mirror would
#      test yesterday's bundle and report today's verdict. Default behaviour is
#      to CHECK and refuse with the exact fix -- `--sync-mirror` opts into the
#      delete-and-recreate, because that mirror is shared with other runs and
#      an entry point should not silently destroy someone else's fixture.
#   2. It resolves the secrets the profile needs (ANTHROPIC_API_KEY for the
#      lanes, GITEA_TOKEN for the rewrite's credential) from the environment or
#      ~/.amplifier/keys.env, and mints a Gitea token if there is none. Never
#      echoed, never passed as a flag that would land in a process list.
#   3. It puts the run's output -- including the manager session's full
#      transcript -- OUTSIDE this repository. A transcript carries prompts and
#      provider responses; none of that belongs in a bundle's git history.
#
# Prerequisites: python3, uv, amplifier-digital-twin, amplifier-gitea, git.
# It fails loud if one is missing rather than degrading into a run that cannot
# mean anything.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
WORKSPACE_ROOT="$(cd "$BUNDLE_ROOT/.." && pwd)"
OUTPUT_ROOT="$WORKSPACE_ROOT/.amplifier/evaluation/converge-turnkey"

# Where a launched container is registered for teardown. A container is a
# MACHINE-WIDE resource, so it belongs in the machine-wide ledger the sweep
# actually reads -- not in a lane-local one nobody sweeps. Measured: with the
# checkout's parent as the default, four containers registered into
# <lane>/infra.tsv, a file the workspace sweep never opens. They were all
# destroyed by the runs themselves, so nothing leaked; but had one survived,
# its row would have been invisible where anyone would look for it.
#
# So: prefer the OUTERMOST ancestor that already keeps an infra.tsv (the shared
# workspace), fall back to the checkout's parent, and let TURNKEY_LEDGER_ROOT
# or an explicit --ledger-root override either.
LEDGER_ROOT="${TURNKEY_LEDGER_ROOT:-}"
if [ -z "$LEDGER_ROOT" ]; then
    LEDGER_ROOT="$WORKSPACE_ROOT"
    probe="$WORKSPACE_ROOT"
    while [ "$probe" != "/" ] && [ "$probe" != "$HOME" ]; do
        [ -f "$probe/infra.tsv" ] && LEDGER_ROOT="$probe"
        probe="$(dirname "$probe")"
    done
fi

GITHUB_REPO="https://github.com/microsoft/amplifier-bundle-converge"
MIRROR_REPO="admin/amplifier-bundle-converge"

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- pass-through args, minus the ones this script consumes ---------------
SYNC_MIRROR=0
SELF_CHECK=0
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --sync-mirror) SYNC_MIRROR=1 ;;
        --self-check)  SELF_CHECK=1; ARGS+=("$arg") ;;
        *)             ARGS+=("$arg") ;;
    esac
done

# The self-check needs no environment at all -- that is its whole point.
if [ "$SELF_CHECK" = 1 ]; then
    exec uv run "$HERE/run.py" "${ARGS[@]}"
fi

# ---- preflight ------------------------------------------------------------
log "preflight"
for tool in python3 uv git amplifier-digital-twin; do
    command -v "$tool" >/dev/null || die "$tool is not on PATH"
done

if [ -f "$HOME/.amplifier/keys.env" ]; then
    set -a; . "$HOME/.amplifier/keys.env"; set +a
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY is not set and not in ~/.amplifier/keys.env. Lanes are agent sessions; without a provider there are no lanes and the wave cannot run."

# ---- the mirror the profile installs from ---------------------------------
# Skipped entirely for --env local, which installs from wherever the README
# says and never launches a container.
case " ${ARGS[*]} " in
    *" --env local "*) NEEDS_MIRROR=0 ;;
    *)                 NEEDS_MIRROR=1 ;;
esac

if [ "$NEEDS_MIRROR" = 1 ]; then
    command -v amplifier-gitea >/dev/null || die "amplifier-gitea is not on PATH; the DTU profile installs the converge bundle from a Gitea mirror"

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
        # `mirror-from-github` refuses (409) when the repo already exists and
        # the CLI has no update verb, so re-syncing IS delete-and-recreate.
        log "re-syncing the mirror: $MIRROR_SHA -> $ORIGIN_SHA"
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
        die "the mirror the DTU profile installs from is not current. Installing from it would test one commit and report a verdict about another. Re-run with --sync-mirror, or sync it yourself."
    fi
    log "mirror is current: $MIRROR_REPO main == github main ($ORIGIN_SHA)"
fi

# ---- output, outside this repository --------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$OUTPUT_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"
log "output: $OUTPUT_DIR"
log "infra ledger: $LEDGER_ROOT/infra.tsv"

# ---- run ------------------------------------------------------------------
set +e
uv run "$HERE/run.py" \
    --ledger-root "$LEDGER_ROOT" \
    --wave-log "$OUTPUT_DIR/manager-session.log" \
    "${ARGS[@]}" > "$OUTPUT_DIR/report.json"
EXIT=$?
set -e

log "harness exit: $EXIT"
log "report:     $OUTPUT_DIR/report.json"
log "transcript: $OUTPUT_DIR/manager-session.log"
exit "$EXIT"
