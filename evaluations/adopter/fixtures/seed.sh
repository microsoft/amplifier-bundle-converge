#!/usr/bin/env bash
# Materialize one of the two adopter scenarios' starting repositories.
#
#   seed.sh new      <target-repo-path>
#   seed.sh existing <target-repo-path> [source-dir]
#
# `new`      -- an empty git repository on `main` with one empty commit. This is
#               the blank slate the new-project scenario starts from: no code,
#               no vision, no contracts, no ledger, no queue.
# `existing` -- the `existing-repo/` fixture, committed as a normal small
#               project's history. Real, runnable Python with passing tests, a
#               README that names two undecided rough edges, and DELIBERATELY no
#               vision, no contracts, no ledger, and no AGENTS.md. That absence
#               IS the fixture: the adopt path has to produce those, so a
#               fixture that already had them could not test it.
#
# It refuses to seed over a non-empty target rather than mix two working trees.
# On success it prints the target path and the seed commit's SHA -- the evidence
# the harness records for the seeding step.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-}"
TARGET="${2:-}"
SOURCE="${3:-$HERE/existing-repo}"

die() { printf 'seed.sh: %s\n' "$*" >&2; exit 1; }

[ -n "$MODE" ] && [ -n "$TARGET" ] || die "usage: seed.sh <new|existing> <target-repo-path> [source-dir]"
command -v git >/dev/null || die "git is not on PATH"

if [ -e "$TARGET" ]; then
    [ -d "$TARGET" ] || die "target exists and is not a directory: $TARGET"
    if [ -n "$(ls -A "$TARGET" 2>/dev/null)" ]; then
        die "target is not empty: $TARGET (refusing to seed over existing work)"
    fi
fi
mkdir -p "$TARGET"
cd "$TARGET"
git init -q -b main
git config user.email "adopter@converge.invalid"
git config user.name "Converge adopter fixture"

case "$MODE" in
    new)
        git commit -q --allow-empty -m "empty repository

Nothing here yet. No vision, no contracts, no code."
        ;;
    existing)
        [ -d "$SOURCE" ] || die "source directory does not exist: $SOURCE"
        cp -R "$SOURCE"/. "$TARGET"/
        git add -A
        git commit -q -m "sensorlog: parse a sensor log, print a report or a summary

A normal small project as it stands the day before anyone adopts a method:
working code, passing tests, a README naming two things nobody has decided.
No vision, no contracts, no ledger, no AGENTS.md."
        ;;
    *)
        die "unknown mode '$MODE' (want: new|existing)"
        ;;
esac

printf '%s %s\n' "$TARGET" "$(git rev-parse HEAD)"
