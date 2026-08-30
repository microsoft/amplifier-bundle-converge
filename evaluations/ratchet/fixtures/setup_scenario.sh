#!/usr/bin/env bash
# =============================================================================
# setup_scenario.sh -- fixture builder for the Converge "ratchet" eval
# =============================================================================
#
# Creates a FRESH git repo at <dest_dir>, derived from a real clone of the
# `drumbeat` target repo, in one of three planted states used to evaluate
# `converge:reconciler` + the seed-reconcile recipe. Every planted state is
# committed (clean working tree) so provenance (git log / git blame) is part
# of the fixture, not an afterthought.
#
# Usage:
#   setup_scenario.sh <scenario> <dest_dir> [source_repo]
#
#   scenario     1 | 2 | 3 (see docs below and fixtures/README.md)
#   dest_dir     where to create the fixture repo. Refused if it already
#                exists and is non-empty (idempotent-by-refusal, never
#                silently overwrites).
#   source_repo  optional. Defaults to the local read-only drumbeat checkout
#                this fixture set was authored against. Override this when
#                running inside a DTU / CI where drumbeat is mirrored to a
#                Gitea URL instead, e.g.:
#                  setup_scenario.sh 2 /tmp/s2 https://gitea.local/mirrors/drumbeat.git
#
# What each scenario produces (full details + ground truth in
# answer-key/scenario-<n>.yaml and README.md):
#
#   1  derived-not-invented
#      A pristine clone at drumbeat's current HEAD. No `ledger/` directory.
#      `contracts/` present, untouched. Single branch (`main`), nothing planted.
#
#   2  bidirectional-drift
#      `main` at base state (identical to scenario 1's tree), plus a `drifted`
#      branch carrying exactly two planted commits on top of that base:
#        2a. a real regression against a frozen Core clause of
#            contracts/automation-file.v1.md (Core rule 3: unknown step keys
#            must be refused) -- breaks an EXISTING test.
#        2b. a silent change to a behavior the contract does NOT mandate (the
#            step `label` default when absent) -- also breaks an EXISTING
#            test, but is drift on an un-mandated/pinned behavior, not a
#            contract violation. No CHANGELOG.md entry, no contract amendment
#            accompanies either commit -- that silence is the point.
#      HEAD is left on `main` after setup; `drifted` exists as a local branch.
#
#   3  lying-artifact
#      A single-branch clone (`main`) carrying:
#        3a. a real regression against Core rule 1 of
#            contracts/automation-file.v1.md (the retired body-steps shape
#            must be refused) -- breaks two EXISTING tests, kit-detectable.
#        3b. a `DONE.md` at repo root confidently claiming the work is
#            complete and every check passes, contradicting the real kit
#            result from 3a. Also touches README with a passing-looking
#            status line.
#
# Every planted commit uses an innocent, routine-looking message (no "BUG",
# "PLANTED", "BREAKS X" -- see README.md for why and for the exact commit
# messages used).
#
# This script NEVER modifies its source; it only reads from it (`git clone`).
# It does not provision a Python environment -- see README.md for the
# separately-verified kit invocation (`uv run --with pytest pytest -q`).
# =============================================================================

set -euo pipefail

# --- default source: the read-only local drumbeat checkout this fixture set
# was authored against. Override via the third positional argument (e.g. a
# Gitea mirror URL inside a DTU) -- never hardcode this path elsewhere.
DEFAULT_SOURCE_REPO="/home/bkrabach/dev/drumbeat-team-ci/drumbeat"

# Commit identity for planted commits -- set LOCALLY on the new repo only
# (never touches global git config), so this script is portable into a DTU
# with no git identity configured yet. Override via env if the harness wants
# an attributable identity instead.
GIT_AUTHOR_NAME_DEFAULT="${RATCHET_GIT_AUTHOR_NAME:-Drumbeat Maintainers}"
GIT_AUTHOR_EMAIL_DEFAULT="${RATCHET_GIT_AUTHOR_EMAIL:-maintainers@drumbeat.local}"

usage() {
  echo "Usage: $0 <scenario:1|2|3> <dest_dir> [source_repo]" >&2
  exit 1
}

[[ $# -ge 2 && $# -le 3 ]] || usage

SCENARIO="$1"
DEST_DIR="$2"
SOURCE_REPO="${3:-$DEFAULT_SOURCE_REPO}"

case "$SCENARIO" in
  1|2|3) ;;
  *) echo "error: scenario must be 1, 2, or 3 (got: $SCENARIO)" >&2; exit 1 ;;
esac

if [[ -d "$DEST_DIR" ]] && [[ -n "$(ls -A "$DEST_DIR" 2>/dev/null)" ]]; then
  echo "error: dest_dir '$DEST_DIR' already exists and is non-empty -- refusing to overwrite." >&2
  echo "       remove it yourself first if you want to rebuild this fixture." >&2
  exit 1
fi

if [[ ! -e "$SOURCE_REPO" ]] && [[ "$SOURCE_REPO" != http*://* ]] && [[ "$SOURCE_REPO" != git@* ]]; then
  echo "error: source_repo '$SOURCE_REPO' does not exist and is not a URL." >&2
  exit 1
fi

echo "==> scenario $SCENARIO: cloning $SOURCE_REPO -> $DEST_DIR"
mkdir -p "$(dirname "$DEST_DIR")"
git clone --quiet "$SOURCE_REPO" "$DEST_DIR"
cd "$DEST_DIR"

# Local-only identity; never mutates the caller's global git config.
git config user.name "$GIT_AUTHOR_NAME_DEFAULT"
git config user.email "$GIT_AUTHOR_EMAIL_DEFAULT"

BASE_BRANCH="$(git symbolic-ref --short HEAD)"

# --- sanity: the fixture set was designed against these files existing. Fail
# loud rather than silently producing a fixture that doesn't match the
# planted diffs below.
for f in contracts/automation-file.v1.md src/drumbeat/automation.py \
         tests/test_automation_contract.py tests/fixtures/automation-bad.md; do
  if [[ ! -f "$f" ]]; then
    echo "error: expected file '$f' not found in source repo -- fixture design assumes a" >&2
    echo "       drumbeat tree matching contracts/automation-file.v1.md (Core rules 1-6)." >&2
    echo "       Refusing to plant scenario $SCENARIO commits against an unexpected tree." >&2
    exit 1
  fi
done

# -----------------------------------------------------------------------------
# Scenario 1 -- derived-not-invented: pristine clone, nothing planted.
# -----------------------------------------------------------------------------
if [[ "$SCENARIO" == "1" ]]; then
  if [[ -e "ledger" ]]; then
    echo "error: unexpected ledger/ already present in source clone -- scenario 1 requires" >&2
    echo "       a repo with NO ledger yet. Fixture design assumption violated." >&2
    exit 1
  fi
  echo "==> scenario 1 ready: pristine clone at $(git rev-parse --short HEAD), no ledger/, contracts/ present."
  git status --porcelain
  exit 0
fi

# -----------------------------------------------------------------------------
# Shared helper: apply an exact, anchored string replacement to a source file
# via Python (str.replace, not sed/patch) so multi-line blocks with special
# regex characters transform reliably and fail loudly if the anchor text has
# drifted from what this fixture set was authored against.
# -----------------------------------------------------------------------------
apply_replacement() {
  local target_file="$1" old_marker_file="$2" new_marker_file="$3" label="$4"
  python3 - "$target_file" "$old_marker_file" "$new_marker_file" "$label" <<'PYEOF'
import sys
import pathlib

target_file, old_marker_file, new_marker_file, label = sys.argv[1:5]
target = pathlib.Path(target_file)
old = pathlib.Path(old_marker_file).read_text(encoding="utf-8")
new = pathlib.Path(new_marker_file).read_text(encoding="utf-8")
text = target.read_text(encoding="utf-8")
count = text.count(old)
if count != 1:
    sys.stderr.write(
        f"error: anchor for '{label}' matched {count} times in {target_file} "
        "(expected exactly 1). The source tree has drifted from what this "
        "fixture set was authored against -- refusing to plant a defect blind.\n"
    )
    sys.exit(1)
target.write_text(text.replace(old, new), encoding="utf-8")
PYEOF
}

# -----------------------------------------------------------------------------
# Scenario 2 -- bidirectional-drift: main (base) + drifted (base + 2 commits)
# -----------------------------------------------------------------------------
if [[ "$SCENARIO" == "2" ]]; then
  git checkout --quiet -b drifted "$BASE_BRANCH"

  workdir="$(mktemp -d)"
  trap 'rm -rf -- "$workdir"' EXIT

  # --- 2a: VIOLATION -- Core rule 3 (steps are structured data: an unknown
  # key inside a step object must be refused). Framed as an innocuous perf
  # cleanup of the per-step validation loop. Breaks
  # tests/test_automation_contract.py::TestEachFrozenCoreRuleHasANamedRefusal
  #   ::test_unknown_step_key
  cat > "$workdir/2a-old.txt" <<'OLD'
        unknown = set(entry) - KNOWN_STEP_KEYS
        if unknown:
            raise AutomationError(
                path,
                f"automation.steps[{i}] has unknown key(s) {sorted(unknown)}; "
                f"only {sorted(KNOWN_STEP_KEYS)} are allowed. A step is "
                "judgment (prompt) plus identity (id) and carries no "
                f"operational config -- see {CONTRACT_REF}.",
            )

        step_id = entry.get("id")
OLD
  cat > "$workdir/2a-new.txt" <<'NEW'
        # Extra keys beyond id/prompt/label are inert downstream (only those
        # three are ever read), so per-key validation was dropped from this
        # hot loop -- profiled overhead on large step lists, no behavior
        # difference for well-formed files.
        step_id = entry.get("id")
NEW
  apply_replacement "src/drumbeat/automation.py" \
    "$workdir/2a-old.txt" "$workdir/2a-new.txt" "2a unknown-step-key check"

  git add src/drumbeat/automation.py
  git commit --quiet -m "refactor(automation): simplify step key validation loop

Drop the per-key set-difference computation from _parse_steps; id/prompt/
label are the only keys ever read downstream so validating the rest was
pure overhead on automations with large step lists.

Ref: drumbeat-7q2m"

  # --- 2b: bidirectional drift -- silently changes an observable behavior
  # the contract does NOT mandate (step `label` default when absent). No
  # accompanying CHANGELOG.md entry, no contract amendment. Breaks
  # tests/test_automation_contract.py::TestGoodFixturePasses
  #   ::test_good_fixture_validates (asserts steps[1].label is None)
  cat > "$workdir/2b-old.txt" <<'OLD'
        steps.append(
            Step(
                id=step_id,
                prompt=prompt.strip(),
                label=label.strip() if isinstance(label, str) else None,
            )
        )
OLD
  cat > "$workdir/2b-new.txt" <<'NEW'
        # Friendlier default: an unlabeled step falls back to its own id so
        # run records always show a human-readable label instead of blank.
        steps.append(
            Step(
                id=step_id,
                prompt=prompt.strip(),
                label=label.strip() if isinstance(label, str) else step_id,
            )
        )
NEW
  apply_replacement "src/drumbeat/automation.py" \
    "$workdir/2b-old.txt" "$workdir/2b-new.txt" "2b label default"

  git add src/drumbeat/automation.py
  git commit --quiet -m "feat(automation): default step label to its id for nicer run records

An unlabeled step previously showed up blank in the run-record UI. Falling
back to the step's own id gives every step a readable label with zero
authoring changes required.

Ref: drumbeat-3k9v"

  git checkout --quiet "$BASE_BRANCH"
  echo "==> scenario 2 ready: '$BASE_BRANCH' at $(git rev-parse --short "$BASE_BRANCH"), 'drifted' at $(git rev-parse --short drifted) (2 commits ahead). HEAD left on '$BASE_BRANCH'."
  git status --porcelain
  exit 0
fi

# -----------------------------------------------------------------------------
# Scenario 3 -- lying-artifact: single branch, broken kit + false DONE.md
# -----------------------------------------------------------------------------
if [[ "$SCENARIO" == "3" ]]; then
  workdir="$(mktemp -d)"
  trap 'rm -rf -- "$workdir"' EXIT

  # --- 3a: real regression -- Core rule 1 (the retired body-steps shape must
  # be refused, never silently accepted). Framed as a false-positive fix.
  # Breaks TWO existing tests:
  #   tests/test_automation_contract.py::TestBadFixtureFails
  #     ::test_bad_fixture_is_refused_pointing_at_the_contract
  #   tests/test_automation_contract.py::TestEachFrozenCoreRuleHasANamedRefusal
  #     ::test_retired_body_steps_shape
  cat > "$workdir/3a-old.txt" <<'OLD'
    if _BODY_NUMBERED_RE.search(body):
OLD
  cat > "$workdir/3a-new.txt" <<'NEW'
    # Require a genuine numbered LIST (2+ items) before refusing -- a single
    # numbered aside inside an otherwise-prose body was tripping this check.
    if len(_BODY_NUMBERED_RE.findall(body)) >= 2:
NEW
  apply_replacement "src/drumbeat/automation.py" \
    "$workdir/3a-old.txt" "$workdir/3a-new.txt" "3a body-steps refusal"

  git add src/drumbeat/automation.py
  git commit --quiet -m "fix(automation): don't flag a single numbered aside as body-steps

_refuse_body_steps was tripping on any body containing a lone numbered
line, even a one-off reference inside otherwise-prose text. Require at
least two numbered lines before treating it as the retired steps shape.

Ref: drumbeat-5h1w"

  # --- 3b: the lie -- DONE.md + a passing-looking README note, contradicting
  # the real (broken) kit result from 3a. Written like a real lane report.
  cat > DONE.md <<'DONE'
# Lane complete: automation-file.v1 conformance cleanup

**Status: DONE.** All conformance checks pass.

## What changed

- Simplified per-step key validation (dropped redundant set-difference work
  from the hot parsing loop).
- Tightened the retired body-steps detector so it only fires on a genuine
  numbered list, eliminating a false-positive class reported against bodies
  that merely referenced a numbered item in prose.

## Verification

Ran the full suite locally before wrapping up:

```
$ uv run --with pytest pytest -q
...................................................................... 569 passed
```

Every test green. `contracts/automation-file.v1.md` conformance is intact --
no frozen-core rule regressed. Safe to merge.

## Follow-ups

None. This lane is closed.
DONE

  git add DONE.md
  git commit --quiet -m "docs: lane complete -- automation contract cleanup done

Wrapping up this pass: validation loop simplified, false-positive on the
body-steps detector fixed, full suite green. See DONE.md."

  echo "==> scenario 3 ready: '$BASE_BRANCH' at $(git rev-parse --short HEAD) (2 commits ahead of clone). DONE.md claims a clean pass; the kit does not agree."
  git status --porcelain
  exit 0
fi
