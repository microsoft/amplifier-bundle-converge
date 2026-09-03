#!/usr/bin/env bash
# Materialize the lumen gap fixture into a target directory as a git repository.
#
#   seed.sh <target-repo-path> [source-dir]
#
# The target is created if absent and must be empty or non-existent -- this
# script refuses to seed over an existing repository rather than silently
# mixing two working trees. On success it prints the target path and the SHA
# of the single seed commit; on failure it exits non-zero with the reason on
# stderr, which is what the harness records as the seeding step's evidence.
#
# The seeded repository is the SYSTEM UNDER TEST's input: two planted gaps in
# two files that do not touch (see answer-key.json). `main` is the base every
# lane branches from.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-}"
SOURCE="${2:-$HERE/gap-repo}"

die() { printf 'seed.sh: %s\n' "$*" >&2; exit 1; }

[ -n "$TARGET" ] || die "usage: seed.sh <target-repo-path> [source-dir]"
[ -d "$SOURCE" ] || die "source directory does not exist: $SOURCE"
command -v git >/dev/null || die "git is not on PATH"

if [ -e "$TARGET" ]; then
    [ -d "$TARGET" ] || die "target exists and is not a directory: $TARGET"
    if [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
        die "target is not empty: $TARGET (refusing to seed over existing work)"
    fi
fi

mkdir -p "$TARGET"
cp -R "$SOURCE"/. "$TARGET"/

cd "$TARGET"
git init -q -b main
git config user.email "turnkey@converge.invalid"
git config user.name "Converge turnkey fixture"
git add -A
git commit -q -m "lumen fixture: two planted gaps, in files that do not touch

contracts/lumen.v1.md is LOCKED. check.py reports both rules FAIL:
  rule 1 (units) -- src/readings.py :: panel_temperature names no unit
  rule 2 (index) -- docs/INDEX.md does not name render_summary

Neither gap's file is the other's, so the two are lane-disjoint."

printf '%s\n' "$TARGET"
git rev-parse HEAD
