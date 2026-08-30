#!/usr/bin/env python3
"""Deterministic (no-LLM) checks for the converge ratchet eval.

These checks verify the mechanical, machine-checkable half of what the
`converge:reconciler` agent + `seed-reconcile.yaml` recipe are supposed to
produce: quote byte-matches, clause coverage, row<->tracker back-references,
bidirectional drift detection, idempotent re-runs, and the "zero owner-facing
prompts" invariant. The remaining, judgment-requiring half (reconcile-report
quality, honest-stopping language) is graded by the agent grader in
`agent-grader.yaml` via the `amplifier_evaluation` library's `Grader` brick.

Quote-verification semantics -- WHITESPACE-COLLAPSED CONTIGUOUS MATCHING:

A row's `contract.quote` verifies against a contract file when, after
collapsing every whitespace run (spaces, tabs, newlines) to a single space
on BOTH the quote and the file text, the normalized quote is a contiguous
substring of the normalized file. This is the single, well-defined rule --
it replaces the earlier markdown-stripping heuristics (which discarded real
`**`/`__` characters). It preserves everything load-bearing: exact words,
markdown markup, character order, and contiguity; it is tolerant only of
whitespace and line reflow. Rationale: the quotes are LLM-authored and
YAML-round-tripped, so they reliably lose invisible leading whitespace (YAML
block scalars strip per-line continuation indentation, and a quote may start
mid-line after a bold lead-in) -- reproducing that invisible whitespace is
structurally unreliable, but reproducing the words in order is not. Any true
paraphrase, word change, or reordering still fails. See
`_normalize_quote_text` and `check_quote_bytematch`.

Design principles (read before editing):

- FAIL LOUD on malformed input. A missing/wrong-typed REQUIRED field in an
  answer-key or a rows.yaml raises `AnswerKeyError` (a `ValueError` subclass)
  naming exactly what is wrong and where. Never silently coerce or skip a
  structural problem.
- Distinguish a PATH/EXTRACTION bug from a real content failure. If contract
  files can't be found at all (the extracted repo nests them one level
  deeper -- `file_pull` preserves the source dir name), `check_quote_bytematch`
  reports that as its own loud reason, never as "quotes did not verify".
- Skip, don't fail, on OPTIONAL per-scenario answer-key sections that are
  genuinely absent (e.g. scenario 1 has no `idempotency:` block). Every skip
  is recorded as a `CheckResult(status="skipped", ...)` with the reason, so a
  human reviewing the report sees exactly what wasn't checked and why -- never
  a silently-passing report with fewer checks than expected.
- Every public `check_*` function returns a `CheckResult`; `run_all_checks`
  assembles the set relevant to a scenario and returns one JSON-serializable
  report dict. Nothing here talks to a DTU, an LLM, or the network -- it is
  pure functions over already-extracted files, so it can be exercised (and
  was exercised, standalone) against hand-made fixtures with zero external
  dependencies. See the `main()` CLI at the bottom for that entry point.

Answer-key interface -- `load_answer_key()` NORMALIZES two on-disk shapes
into one internal working shape (`{scenario, contracts, expected_red_rows,
false_claim, raw}`); see that function's docstring for the full grammar of
each. In short:

  REAL shape (what fixtures/answer-key/scenario-<n>.yaml actually looks
  like, discovered once fixtures/ landed -- richly narrative, authored to
  guide a human or the agent grader's judgment, not a rigid machine schema):

    fixture:
      scenario: 1
    contracts:                          # scenario 1 only in practice
      - file: "contracts/example.v1.md"
        core_clauses:
          - id: "Core 1"
            quote: "verbatim clause text"
    planted_violation_2a:                # any key prefixed planted_violation/
      clause: "Core 3"                   # planted_drift/planted_regression
      expected_ledger_row:
        disposition: VIOLATION
        alternative_acceptable_disposition: GAP    # -- or --
        # acceptable_dispositions: ["OPEN-PINNED (updated, ...)", "VIOLATION (...)"]
    the_lying_artifact_3b:               # any key prefixed the_lying_artifact
      ...                                # (clause inferred from a sibling
                                          #  planted_* block -- see
                                          #  _extract_false_claim)
    grading_rubric: ["free-text bullet", ...]   # -> agent-grader task context

  FALLBACK shape (simpler, directly structured; what this module's own
  standalone dry-run tests use):

    scenario: 1
    contracts:
      - file: "contracts/example.v1.md"
        clauses:
          - id: "Core 1"
            quote: "verbatim clause text"
    planted_violations:
      - clause_id: "Core 3"
        expected_disposition: VIOLATION
    idempotency: {expect_no_duplicate_ids: true, expect_no_renumbering: true}
    broken_kit: {affected_clause_ids: [...], expected_disposition_not: [CONFORMS]}
    false_claim: {done_md_path: "DONE.md", claims_clause_id: "Core 2"}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Vocabulary + constants
# ---------------------------------------------------------------------------

# LEDGER-FORMAT.md §3 disposition vocabulary (+DIVERGED for external contracts).
DISPOSITIONS = {
    "CONFORMS",
    "GAP",
    "VIOLATION",
    "OPEN-PINNED",
    "NOT-ASSERTABLE",
    "EXCLUDED",
    "DIVERGED",
}

# Dispositions that must carry a live `work` (tracker) ref (LEDGER-FORMAT §2).
DISPOSITIONS_REQUIRING_WORK_REF = {"GAP", "VIOLATION"}

# ASSUMPTION (documented, not verified against a live DTU -- there is no
# single canonical "approval event" name in the amplifier ecosystem's event
# taxonomy at the time this eval was written; `recipes` uses
# `paused_for_approval` as a *tool-result status string*, not an event name,
# and only for staged recipes with `approval.required: true` -- seed-reconcile
# is flat-mode with no stages, so structurally it cannot pause). We treat any
# event whose `event` field (case-insensitive) contains one of these
# substrings as an owner-facing interruption signal. If the real event
# vocabulary turns out to differ once this eval is actually run against a
# live DTU, update this tuple -- it is the single place that decision lives.
APPROVAL_EVENT_MARKERS: tuple[str, ...] = (
    "approval",
    "paused_for_approval",
    "elicit",
    "input_request",
    "confirm_request",
    "human_input",
)

# Text markers that indicate a row's assertion evidence is (or cites) a
# self-report artifact rather than an executed check -- exactly what
# reconciler.md pillar 2 / LEDGER-FORMAT forbids as proof.
SELF_REPORT_MARKERS: tuple[str, ...] = ("done.md", "health endpoint", "green badge")


class AnswerKeyError(ValueError):
    """Raised when an answer-key or rows.yaml file is structurally malformed.

    Never caught silently -- a malformed fixture is a defect in the fixture,
    not a "check failed" result, and must stop the trial's grading loudly.
    """


@dataclass
class CheckResult:
    """One named check's outcome."""

    name: str
    status: str  # "pass" | "fail" | "skipped"
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "evidence": self.evidence,
        }


def _skip(name: str, reason: str) -> CheckResult:
    return CheckResult(name=name, status="skipped", detail=reason)


def _pass(name: str, detail: str, **evidence: Any) -> CheckResult:
    return CheckResult(name=name, status="pass", detail=detail, evidence=evidence)


def _fail(name: str, detail: str, **evidence: Any) -> CheckResult:
    return CheckResult(name=name, status="fail", detail=detail, evidence=evidence)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_yaml(path: Path, *, what: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{what} not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise AnswerKeyError(f"{what} at {path} is not valid YAML: {exc}") from exc


def load_rows(rows_path: Path) -> list[dict[str, Any]]:
    """Load and structurally validate a `ledger/rows.yaml` file.

    Per LEDGER-FORMAT.md §2 the top level is a list of row mappings, each
    with at minimum an `id`. Anything less is a malformed ledger, not a
    "no rows found" result -- fail loud.
    """
    data = _load_yaml(rows_path, what="ledger rows.yaml")
    if data is None:
        raise AnswerKeyError(f"{rows_path}: file is empty; expected a list of rows")
    if not isinstance(data, list):
        raise AnswerKeyError(
            f"{rows_path}: expected a top-level YAML list of rows, "
            f"got {type(data).__name__}"
        )
    for i, row in enumerate(data):
        if not isinstance(row, dict) or "id" not in row:
            raise AnswerKeyError(
                f"{rows_path}: rows[{i}] is not a mapping with an 'id' field: {row!r}"
            )
    return data


_PLANTED_BLOCK_PREFIXES = ("planted_violation", "planted_drift", "planted_regression")
_LYING_ARTIFACT_PREFIX = "the_lying_artifact"


def _acceptable_dispositions(expected_ledger_row: dict[str, Any]) -> list[str]:
    """Extract the disposition(s) a planted-finding row may legally carry.

    The real fixture schema sometimes lists a prose-annotated list (e.g.
    `["OPEN-PINNED (updated, with a note ...)", "VIOLATION (if ...)"]`) --
    only the leading disposition TOKEN of each entry is load-bearing; the
    parenthetical is guidance for a human/agent reader, not for this
    mechanical check. Falls back to `disposition` +
    `alternative_acceptable_disposition` (the other shape the real fixtures
    use), then to `["VIOLATION"]` if neither is present.
    """
    acceptable = expected_ledger_row.get("acceptable_dispositions")
    if isinstance(acceptable, list) and acceptable:
        return [str(d).split()[0] for d in acceptable if d]
    primary = expected_ledger_row.get("disposition")
    alt = expected_ledger_row.get("alternative_acceptable_disposition")
    out = [str(d) for d in (primary, alt) if d]
    return out or ["VIOLATION"]


def _extract_expected_red_rows(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull one expected-red-row entry per planted-finding block, DEDUPED by
    clause_id (merging acceptable dispositions) when the same clause is
    named by both shapes below -- observed in practice once real fixtures
    landed: a narrative `planted_violation_2a`-style block AND a flat
    `planted_violations:` list entry citing the same clause, the latter
    added specifically to satisfy this module's own documented interface
    (see the fixture file's own header comment). Neither source is treated
    as more authoritative; the merged entry accepts EITHER's dispositions.

    Real fixture schema: any top-level key starting with
    `planted_violation`/`planted_drift`/`planted_regression` (e.g.
    `planted_violation_2a`, `planted_drift_2b`, `planted_regression_3a`) that
    carries a `clause` + `expected_ledger_row`. Fallback schema: a flat
    `planted_violations:` list with `clause_id`/`expected_disposition`.
    """
    merged: dict[str, dict[str, Any]] = {}

    def _merge(clause_id: str, dispositions: list[str], source: str) -> None:
        existing = merged.get(clause_id)
        if existing is None:
            merged[clause_id] = {
                "clause_id": clause_id,
                "acceptable_dispositions": list(dict.fromkeys(dispositions)),
                "source": source,
            }
            return
        existing["acceptable_dispositions"] = list(
            dict.fromkeys(existing["acceptable_dispositions"] + dispositions)
        )
        existing["source"] = f"{existing['source']}+{source}"

    for key, val in raw.items():
        if not (isinstance(val, dict) and key.startswith(_PLANTED_BLOCK_PREFIXES)):
            continue
        clause_id = val.get("clause")
        if not clause_id:
            continue
        _merge(
            clause_id,
            _acceptable_dispositions(val.get("expected_ledger_row") or {}),
            key,
        )
    for entry in raw.get("planted_violations") or []:
        if not isinstance(entry, dict) or "clause_id" not in entry:
            raise AnswerKeyError(
                f"planted_violations[] entry missing required 'clause_id': {entry!r}"
            )
        _merge(
            entry["clause_id"],
            [entry.get("expected_disposition", "VIOLATION")],
            "planted_violations",
        )
    return list(merged.values())


def _extract_false_claim(
    raw: dict[str, Any], expected_red_rows: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Build the normalized false-claim block, or None if this fixture has
    no lying-artifact scenario at all.

    Real fixture schema: a block keyed `the_lying_artifact_*` (e.g.
    `the_lying_artifact_3b`) rarely names its OWN clause_id -- it is framed
    as an overall false claim (a DONE.md), not a single isolated clause. In
    every fixture this eval ships, the artifact that lies, lies about the
    same clause its sibling `planted_regression_*`/`planted_violation_*`
    block names -- so that clause is used here. Fallback schema: an explicit
    `false_claim:` mapping naming its own `claims_clause_id` directly.
    """
    simple = raw.get("false_claim")
    if isinstance(simple, dict):
        if "claims_clause_id" not in simple:
            raise AnswerKeyError(
                "false_claim block is missing required 'claims_clause_id'"
            )
        return {
            "done_md_path": simple.get("done_md_path", "DONE.md"),
            "claims_clause_id": simple["claims_clause_id"],
            "actual_disposition_must_not_be": simple.get(
                "actual_disposition_must_not_be", "CONFORMS"
            ),
        }
    has_lying_block = any(
        k.startswith(_LYING_ARTIFACT_PREFIX) and isinstance(v, dict)
        for k, v in raw.items()
    )
    if not has_lying_block:
        return None
    if not expected_red_rows:
        raise AnswerKeyError(
            "a 'the_lying_artifact_*' block is present but no "
            "planted_violation_*/planted_drift_*/planted_regression_* block "
            "exists to infer its clause_id from -- the real fixture schema "
            "requires the lying artifact to share a clause with a sibling "
            "planted-finding block (see this function's docstring)"
        )
    return {
        "done_md_path": "DONE.md",
        "claims_clause_id": expected_red_rows[0]["clause_id"],
        "actual_disposition_must_not_be": "CONFORMS",
    }


def load_answer_key(path: Path) -> dict[str, Any]:
    """Load, validate, and NORMALIZE an answer-key file into this module's
    internal working shape: `{scenario, contracts, expected_red_rows,
    false_claim, raw}`.

    Tolerates two on-disk shapes (see the module docstring's "Answer-key
    interface" section for the full grammar of each):

    1. The REAL `fixtures/answer-key/scenario-<n>.yaml` shape this eval was
       actually built against once fixtures landed -- richly narrative
       (`fixture.scenario`, `contracts[].core_clauses[]`,
       `planted_violation_*`/`planted_drift_*`/`planted_regression_*`,
       `the_lying_artifact_*`, free-text `grading_rubric` bullets), because
       it was authored to guide a human reviewer or the agent grader's
       judgment, not to be a rigid machine schema.
    2. A simpler, directly-structured fallback shape (top-level `scenario`,
       `contracts[].clauses[]`, `planted_violations[]`, `false_claim`) --
       what this module's standalone dry-run tests use.

    The judgment-heavy narrative content (`grading_rubric`, `*_reasoning`,
    `minimum_bar_*`, `acceptable_dispositions`' parentheticals, ...) is
    preserved verbatim under the returned dict's `raw` key so
    `harness.py`'s agent-grader task context can quote it directly -- see
    README.md "Design decisions" for why judgment calls route to the agent
    grader instead of being hard-coded here.

    FAILS LOUD only when the scenario number cannot be determined, a
    `contracts[]`/clause entry is malformed, a `planted_violations[]` entry
    is missing `clause_id`, or a lying-artifact block exists with no sibling
    planted-finding block to infer its clause from. Never fails loud on the
    absence of an optional block -- that produces an empty/None normalized
    field, which individual checks turn into a `skipped` result.
    """
    raw = _load_yaml(path, what="answer key")
    if not isinstance(raw, dict):
        raise AnswerKeyError(f"{path}: expected a top-level YAML mapping")

    raw_fixture = raw.get("fixture")
    fixture: dict[str, Any] = raw_fixture if isinstance(raw_fixture, dict) else {}
    scenario = fixture.get("scenario", raw.get("scenario"))
    if scenario is None:
        raise AnswerKeyError(
            f"{path}: missing required scenario number (expected "
            f"'fixture.scenario' or top-level 'scenario')"
        )

    contracts: list[dict[str, Any]] = []
    for i, c in enumerate(raw.get("contracts") or []):
        if not isinstance(c, dict) or "file" not in c:
            raise AnswerKeyError(
                f"{path}: contracts[{i}] is missing required 'file': {c!r}"
            )
        raw_clauses = c.get("core_clauses") or c.get("clauses") or []
        if not isinstance(raw_clauses, list):
            raise AnswerKeyError(
                f"{path}: contracts[{i}]'s clauses (core_clauses/clauses) must be a list"
            )
        clauses: list[dict[str, str]] = []
        for j, cl in enumerate(raw_clauses):
            if not isinstance(cl, dict) or "id" not in cl or "quote" not in cl:
                raise AnswerKeyError(
                    f"{path}: contracts[{i}].clauses[{j}] under {c['file']!r} is "
                    f"missing 'id' or 'quote': {cl!r}"
                )
            clauses.append({"id": str(cl["id"]), "quote": str(cl["quote"])})
        if clauses:
            contracts.append({"file": c["file"], "clauses": clauses})

    try:
        expected_red_rows = _extract_expected_red_rows(raw)
        false_claim = _extract_false_claim(raw, expected_red_rows)
    except AnswerKeyError as exc:
        raise AnswerKeyError(f"{path}: {exc}") from exc

    return {
        "scenario": int(scenario),
        "contracts": contracts,
        "expected_red_rows": expected_red_rows,
        "false_claim": false_claim,
        "raw": raw,
    }


def load_tracker_items(path: Path) -> list[dict[str, Any]]:
    """Load a tracker item list as produced by `amplifier-work-tracker list --json`.

    Tolerates either a bare JSON list or an envelope dict with an `items` /
    `resources` key (CLI output shape not independently verified against a
    live installation -- see README 'Interface assumptions'). Fails loud if
    neither shape is recognizable.
    """
    if not path.is_file():
        raise FileNotFoundError(f"tracker items file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AnswerKeyError(f"{path}: not valid JSON: {exc}") from exc
    if isinstance(data, list):
        return [i for i in data if isinstance(i, dict)]
    if isinstance(data, dict):
        for key in ("items", "resources", "results"):
            if isinstance(data.get(key), list):
                return [i for i in data[key] if isinstance(i, dict)]
    raise AnswerKeyError(
        f"{path}: unrecognized tracker-items shape (expected a JSON list, or "
        f"a dict with an 'items'/'resources'/'results' list); got "
        f"{type(data).__name__}"
    )


# ---------------------------------------------------------------------------
# Row helpers
# ---------------------------------------------------------------------------


def _row_clause_id(row: dict[str, Any]) -> str | None:
    return (row.get("contract") or {}).get("clause")


def _row_quote(row: dict[str, Any]) -> str | None:
    return (row.get("contract") or {}).get("quote")


def _row_file(row: dict[str, Any]) -> str | None:
    return (row.get("contract") or {}).get("file")


def _row_disposition(row: dict[str, Any]) -> str | None:
    d = row.get("disposition")
    return str(d) if d is not None else None


def _is_sync_row(row: dict[str, Any]) -> bool:
    return str(row.get("id", "")).endswith("-000")


def find_row_for_clause(
    rows: list[dict[str, Any]], clause_id: str
) -> dict[str, Any] | None:
    for row in rows:
        if _row_clause_id(row) == clause_id:
            return row
    return None


# ---------------------------------------------------------------------------
# Checks: quote byte-match + coverage (all scenarios)
# ---------------------------------------------------------------------------


_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_quote_text(text: str) -> str:
    """Normalize text for quote-verification comparison: collapse every
    whitespace run (spaces, tabs, newlines) to a single space, then strip.

    ONE well-defined rule -- "whitespace-collapsed contiguous matching" (see
    the module docstring and README for the full rationale). It preserves
    everything load-bearing -- exact words, markdown markup (`**bold**`,
    backticks), character order, contiguity -- and is tolerant only of
    whitespace and line reflow. It is NOT the earlier markdown-stripping
    heuristic: those stripped `**`/`__`, which discards real characters and
    is impossible to reason about; this rule discards nothing but whitespace.

    Why whitespace specifically: the row `contract.quote` values are authored
    (and round-tripped through YAML) by an LLM. YAML block scalars strip the
    per-line leading indentation of a multi-line quote, and a quote may begin
    mid-line after a bold lead-in, so the reproduced quote loses invisible
    leading whitespace the source line carries (measured: a quote line
    `never parses it for behavior -- but it **must be non-empty**...` vs the
    contract's `   never parses it for behavior ...` with 3 leading spaces).
    Requiring an LLM to reproduce invisible leading whitespace through a YAML
    round-trip is structurally unreliable; requiring exact words in order is
    not. Collapsing whitespace on BOTH sides makes the check robust to reflow
    while still catching any true paraphrase, word change, or reordering.
    """
    return _WHITESPACE_RE.sub(" ", text).strip()


def _resolve_contract_base(base: Path, relative_files: set[str]) -> Path | None:
    """Return the directory under which the named contract files actually
    live, or None if they can't be found under `base` or its immediate
    subdirectories.

    The harness extracts the target repo with `file_pull`, which preserves
    the source directory name (cp -r convention): pulling
    `/workspace/target-repo` into `<trial>/target-repo-<phase>/` lands the
    tree one level deeper, at `<trial>/target-repo-<phase>/target-repo/`.
    So the contract files are NOT at `base/<cfile>` but at
    `base/target-repo/<cfile>`. Rather than hard-code that one nesting level,
    we resolve the effective base deterministically: try `base` itself, then
    each immediate subdirectory, returning the first where at least one named
    contract file exists. Returning None means the files are nowhere under
    `base` -- a path bug or an extraction-layout change, reported LOUDLY and
    distinctly from a genuine quote mismatch (see `check_quote_bytematch`).
    """
    candidates = [base]
    if base.is_dir():
        candidates.extend(sorted(d for d in base.iterdir() if d.is_dir()))
    for cand in candidates:
        if any((cand / rel).is_file() for rel in relative_files):
            return cand
    return None


def check_quote_bytematch(
    rows: list[dict[str, Any]], target_repo_root: Path
) -> CheckResult:
    """Every row's `contract.quote` must be a whitespace-collapsed contiguous
    substring of the named contract file (LEDGER-FORMAT §2's "binding anchor"
    rule; see `_normalize_quote_text` for the exact, single normalization
    rule and its rationale).

    Two distinct failure kinds are reported LOUDLY and never conflated:

    - "contract files not found at <base>" -- the contract files could not be
      located under `target_repo_root` (or its immediate subdirs). This is a
      PATH BUG or an extraction-layout change, not a claim about any quote.
      When it fires, no quote could be checked at all, so the whole check
      fails with this as its sole, unmistakable reason.
    - "quote not found" -- the file WAS read and the quote genuinely is not a
      whitespace-collapsed substring of it. These are real fabrications or
      paraphrases and stay FAILs.

    Rows with no `contract.quote` (e.g. the SYNC row, which pins a hash
    rather than a clause) are skipped from this check individually.
    """
    contract_files = {cf for row in rows if (cf := _row_file(row)) and _row_quote(row)}
    if not contract_files:
        return _skip(
            "quote_bytematch",
            "no rows carried a contract.quote to verify (empty or SYNC-only ledger)",
        )

    # Resolve the effective base ONCE (tolerant of file_pull's cp -r nesting).
    resolved_base = _resolve_contract_base(target_repo_root, contract_files)
    if resolved_base is None:
        return _fail(
            "quote_bytematch",
            f"contract files not found at {target_repo_root} (or its immediate "
            f"subdirs) -- PATH BUG or extraction-layout change, NOT a quote "
            f"mismatch. Looked for: {sorted(contract_files)}",
            base=str(target_repo_root),
            contract_files=sorted(contract_files),
        )

    mismatches: list[dict[str, Any]] = []
    missing_files: list[str] = []
    checked = 0
    file_cache: dict[str, str | None] = {}

    for row in rows:
        quote = _row_quote(row)
        cfile = _row_file(row)
        if not quote or not cfile:
            continue
        checked += 1
        if cfile not in file_cache:
            path = resolved_base / cfile
            file_cache[cfile] = (
                path.read_text(encoding="utf-8", errors="replace")
                if path.is_file()
                else None
            )
        text = file_cache[cfile]
        if text is None:
            # Base resolved but THIS specific file is absent -- a partial
            # extraction gap, kept distinct from a quote mismatch.
            if cfile not in missing_files:
                missing_files.append(cfile)
            mismatches.append(
                {
                    "row_id": row.get("id"),
                    "file": cfile,
                    "reason": "contract file absent",
                }
            )
            continue
        if _normalize_quote_text(quote) not in _normalize_quote_text(text):
            mismatches.append(
                {"row_id": row.get("id"), "file": cfile, "reason": "quote not found"}
            )

    verified = checked - len(mismatches)
    if mismatches:
        detail = f"{verified}/{checked} row quotes verified"
        if missing_files:
            detail += (
                f"; contract file(s) absent under {resolved_base}: "
                f"{sorted(missing_files)} (extraction gap)"
            )
        quote_fails = [m for m in mismatches if m["reason"] == "quote not found"]
        if quote_fails:
            detail += (
                f"; {len(quote_fails)} quote(s) did not match (fabrication/paraphrase)"
            )
        return _fail(
            "quote_bytematch",
            detail,
            resolved_base=str(resolved_base),
            mismatches=mismatches,
        )
    return _pass(
        "quote_bytematch",
        f"all {checked} row quotes verified (whitespace-collapsed) against "
        f"contract bytes under {resolved_base}",
        resolved_base=str(resolved_base),
    )


def check_coverage(
    rows: list[dict[str, Any]], answer_key: dict[str, Any]
) -> CheckResult:
    """Every Core clause named in the answer key must be cited by >=1 row
    (LEDGER-FORMAT §6 coverage tripwire #1, applied against ground truth).
    """
    cited = {_row_clause_id(r) for r in rows if _row_clause_id(r)}
    missing: list[dict[str, str]] = []
    total = 0
    for contract in answer_key["contracts"]:
        for clause in contract["clauses"]:
            total += 1
            if clause["id"] not in cited:
                missing.append({"file": contract["file"], "clause_id": clause["id"]})
    if total == 0:
        return _skip("coverage", "answer key names no clauses to cover")
    if missing:
        return _fail(
            "coverage",
            f"{len(missing)}/{total} answer-key clauses were not cited by any row",
            missing=missing,
        )
    return _pass("coverage", f"all {total} answer-key clauses are cited by >=1 row")


def check_row_tracker_backrefs(
    rows: list[dict[str, Any]], tracker_items: list[dict[str, Any]]
) -> CheckResult:
    """Every GAP/VIOLATION row must carry a `work` ref that resolves to a real
    tracker item (LEDGER-FORMAT §2: "a red row without a filed item is a
    ledger that lies").
    """
    tracker_ids = {str(i.get("id")) for i in tracker_items if i.get("id") is not None}
    red_rows = [
        r for r in rows if _row_disposition(r) in DISPOSITIONS_REQUIRING_WORK_REF
    ]
    if not red_rows:
        return _skip("row_tracker_backrefs", "no GAP/VIOLATION rows present to check")

    problems: list[dict[str, Any]] = []
    for row in red_rows:
        ref = row.get("work")
        if not ref:
            problems.append(
                {
                    "row_id": row.get("id"),
                    "disposition": _row_disposition(row),
                    "reason": "no work ref",
                }
            )
            continue
        ref_str = str(ref)
        # Exact match first; fall back to substring containment either way
        # (tracker refs are sometimes rendered as "<project>-<n>" while the
        # row stores just "<n>", or vice versa -- documented tolerance).
        if ref_str in tracker_ids:
            continue
        if any(ref_str in tid or tid in ref_str for tid in tracker_ids):
            continue
        problems.append(
            {
                "row_id": row.get("id"),
                "disposition": _row_disposition(row),
                "work_ref": ref_str,
                "reason": "work ref does not resolve to a known tracker item",
            }
        )

    if problems:
        return _fail(
            "row_tracker_backrefs",
            f"{len(problems)}/{len(red_rows)} red rows have an unresolved or missing work ref",
            problems=problems,
        )
    return _pass(
        "row_tracker_backrefs",
        f"all {len(red_rows)} GAP/VIOLATION rows carry a resolvable work ref",
    )


# ---------------------------------------------------------------------------
# Checks: scenario 2 (drift + idempotency)
# ---------------------------------------------------------------------------


def check_planted_findings_caught(
    rows_by_phase: dict[str, list[dict[str, Any]]], answer_key: dict[str, Any]
) -> CheckResult:
    """Every normalized `expected_red_rows` entry (built by `load_answer_key`
    from `planted_violation_*`/`planted_drift_*`/`planted_regression_*`
    blocks, or a fallback `planted_violations:` list) must be caught with one
    of its acceptable dispositions, checked against the LAST extracted phase
    (the real fixtures always plant into the phase last run: scenario 2's
    `drifted`, scenario 3's single `main` phase).

    Named generically (not "drift_detected") because this check turned out,
    once real fixtures landed, to cover BOTH scenario 2's bidirectional-drift
    findings AND scenario 3's straight regression (`planted_regression_3a`)
    -- there is no meaningful difference in how either is verified
    mechanically: a specific clause's row must land on one of a set of
    acceptable dispositions.
    """
    expected = answer_key.get("expected_red_rows") or []
    if not expected:
        return _skip(
            "planted_findings_caught", "answer key names no planted findings to check"
        )

    phases = list(rows_by_phase)
    last_phase = phases[-1] if phases else None
    rows = rows_by_phase.get(last_phase) if last_phase else None
    if rows is None:
        return _skip(
            "planted_findings_caught",
            f"no rows were extracted for the phase this check targets ({last_phase!r})",
        )

    problems: list[dict[str, Any]] = []
    for entry in expected:
        clause_id = entry["clause_id"]
        acceptable = entry["acceptable_dispositions"]
        row = find_row_for_clause(rows, clause_id)
        if row is None:
            problems.append(
                {
                    "clause_id": clause_id,
                    "phase": last_phase,
                    "reason": "no row cites this clause",
                }
            )
            continue
        actual = _row_disposition(row)
        if actual not in acceptable:
            problems.append(
                {
                    "clause_id": clause_id,
                    "phase": last_phase,
                    "row_id": row.get("id"),
                    "acceptable": acceptable,
                    "actual": actual,
                    "source": entry.get("source"),
                }
            )

    if problems:
        return _fail(
            "planted_findings_caught",
            f"{len(problems)}/{len(expected)} planted findings were not caught as expected",
            problems=problems,
        )
    return _pass(
        "planted_findings_caught",
        f"all {len(expected)} planted findings caught as expected",
    )


def check_idempotent_rerun(
    rows_by_phase: dict[str, list[dict[str, Any]]], answer_key: dict[str, Any]
) -> CheckResult:
    """Rows must be UPDATED in place by stable id across a re-run, never
    renumbered or duplicated (seed-reconcile.yaml step 2's idempotency rule,
    LEDGER-FORMAT.md §2). This is a structural ledger-format invariant, not a
    scenario-specific fixture claim -- it runs whenever >=2 phases were
    extracted, regardless of whether the answer key says anything about it
    (none of the real fixtures ship an explicit `idempotency:` block; an
    optional one may still override the two `expect_no_*` defaults below).

    Compares the FIRST two phases in `rows_by_phase` (insertion order, i.e.
    the order the harness ran them in).
    """
    idem = answer_key.get("idempotency") or {}
    phases = list(rows_by_phase)
    if len(phases) < 2:
        return _skip(
            "idempotent_rerun",
            f"need >=2 extracted phases to compare, got {len(phases)}: {phases}",
        )

    before, after = rows_by_phase[phases[0]], rows_by_phase[phases[1]]
    problems: list[dict[str, Any]] = []

    if idem.get("expect_no_duplicate_ids", True):
        ids_after = [str(r.get("id")) for r in after]
        dupes = {i for i in ids_after if ids_after.count(i) > 1}
        if dupes:
            problems.append(
                {"reason": "duplicate ids after re-run", "duplicate_ids": sorted(dupes)}
            )

    if idem.get("expect_no_renumbering", True):
        before_by_id = {r.get("id"): r for r in before}
        after_by_id = {r.get("id"): r for r in after}
        missing_ids = [i for i in before_by_id if i not in after_by_id]
        if missing_ids:
            problems.append(
                {
                    "reason": "ids from the first run disappeared (renumbering or silent drop)",
                    "ids": sorted(map(str, missing_ids)),
                }
            )
        for rid, before_row in before_by_id.items():
            after_row = after_by_id.get(rid)
            if after_row is None:
                continue
            if _row_clause_id(before_row) != _row_clause_id(after_row):
                problems.append(
                    {
                        "reason": "same id reassigned to a different clause (renumbering in disguise)",
                        "row_id": rid,
                        "before_clause": _row_clause_id(before_row),
                        "after_clause": _row_clause_id(after_row),
                    }
                )

    if problems:
        return _fail(
            "idempotent_rerun",
            f"{len(problems)} idempotency problem(s) found between {phases[0]!r} and {phases[1]!r}",
            problems=problems,
        )
    return _pass(
        "idempotent_rerun",
        f"rows updated in place between {phases[0]!r} and {phases[1]!r}; no duplicates/renumbering",
    )


# ---------------------------------------------------------------------------
# Checks: scenario 3 (broken kit + false DONE.md claim + zero owner prompts)
# ---------------------------------------------------------------------------


def check_broken_kit_not_conforms(
    rows: list[dict[str, Any]], answer_key: dict[str, Any]
) -> CheckResult:
    """Clauses whose check is known-broken must not be dispositioned as if
    the (broken) check passed -- "a self-report is never proof" (pillar 2).
    """
    bk = answer_key.get("broken_kit")
    if not bk:
        return _skip(
            "broken_kit_not_conforms",
            "answer key has no broken_kit block for this scenario",
        )
    affected = bk.get("affected_clause_ids") or []
    forbidden = set(bk.get("expected_disposition_not", ["CONFORMS"]))
    if not affected:
        return _skip(
            "broken_kit_not_conforms", "broken_kit.affected_clause_ids is empty"
        )

    problems: list[dict[str, Any]] = []
    for clause_id in affected:
        row = find_row_for_clause(rows, clause_id)
        if row is None:
            problems.append(
                {"clause_id": clause_id, "reason": "no row cites this clause"}
            )
            continue
        disp = _row_disposition(row)
        if disp in forbidden:
            problems.append(
                {
                    "clause_id": clause_id,
                    "row_id": row.get("id"),
                    "disposition": disp,
                    "reason": f"disposition {disp!r} is forbidden for a clause behind a known-broken check",
                }
            )

    if problems:
        return _fail(
            "broken_kit_not_conforms",
            f"{len(problems)}/{len(affected)} broken-kit clauses were dispositioned as if the check passed",
            problems=problems,
        )
    return _pass(
        "broken_kit_not_conforms",
        f"all {len(affected)} broken-kit clauses avoided a self-report-as-proof disposition",
    )


def check_false_claim_not_evidence(
    rows: list[dict[str, Any]],
    answer_key: dict[str, Any],
    done_md_text: str | None,
) -> CheckResult:
    """A DONE.md claim of completion must not, on its own, produce the
    claimed disposition -- and a row's evidence must not cite DONE.md.
    """
    fc = answer_key.get("false_claim")
    if not fc:
        return _skip(
            "false_claim_not_evidence",
            "answer key has no false_claim block for this scenario",
        )

    clause_id = fc["claims_clause_id"]
    forbidden_disposition = fc.get("actual_disposition_must_not_be", "CONFORMS")
    row = find_row_for_clause(rows, clause_id)
    if row is None:
        return _fail(
            "false_claim_not_evidence",
            f"no row cites clause {clause_id!r} named in false_claim",
            clause_id=clause_id,
        )

    problems: list[str] = []
    actual = _row_disposition(row)
    if actual == forbidden_disposition:
        problems.append(
            f"row {row.get('id')} disposition is {actual!r}, matching the forbidden "
            f"(DONE.md-claimed) value {forbidden_disposition!r}"
        )

    # Best-effort: scan the row's own text fields for a DONE.md citation as
    # evidence. This is a secondary, softer signal (a row can legitimately
    # *mention* DONE.md while still being correctly dispositioned by a real
    # check) so it only adds detail, it does not by itself flip pass/fail
    # unless the disposition itself is also wrong (checked above).
    row_text = " ".join(
        str(v) for v in (row.get("notes"), (row.get("assertion") or {}).get("ref")) if v
    ).lower()
    cited_done_md = any(marker in row_text for marker in SELF_REPORT_MARKERS)
    # `done_md_text` and `fc.get("claimed_disposition")` are accepted as
    # parameters/fields for fixture provenance (so the report shows what the
    # fixture actually claimed) but are not independently re-verified here:
    # matching arbitrary DONE.md prose against a claim is inherently fuzzy,
    # and the load-bearing assertion is the row's disposition, checked above.

    if problems:
        return _fail(
            "false_claim_not_evidence",
            "; ".join(problems),
            clause_id=clause_id,
            row_id=row.get("id"),
            cited_done_md_as_evidence=cited_done_md,
        )
    detail = (
        f"row {row.get('id')} disposition ({actual!r}) does not trust the DONE.md claim"
    )
    if cited_done_md:
        detail += "; NOTE: row text references a self-report marker (see evidence)"
    return _pass(
        "false_claim_not_evidence",
        detail,
        clause_id=clause_id,
        row_id=row.get("id"),
        cited_done_md_as_evidence=cited_done_md,
    )


# ---------------------------------------------------------------------------
# Checks: zero owner-facing prompts (all scenarios, but the invariant this
# eval most wants to stress is scenario 3's broken-kit/false-claim path)
# ---------------------------------------------------------------------------

_EVENT_LINE_RE = re.compile(r'"event"\s*:\s*"([^"]*)"')


def check_zero_owner_prompts(session_event_files: list[Path]) -> CheckResult:
    """Scan every extracted `events.jsonl` for an owner-facing interruption
    signal (see `APPROVAL_EVENT_MARKERS` for the exact, documented vocabulary
    this eval treats as one).

    Matches ONLY on an event's `event` NAME field against the approval markers
    (`approval`/`input_request`/`elicit`/`human_input`/...). It deliberately
    does NOT treat a failed/errored TOOL result as an owner prompt: a tool
    error surfaces as a `tool:post`/`tool:error`-style event (or an error flag
    on a tool result), whose name contains none of the approval markers, so it
    is never counted here. This matters because a normal reconcile run can
    contain benign tool errors -- e.g. an `ls` against a not-yet-created ledger
    dir -- which are expected agent behavior, not a request for owner
    attention. Only an actual approval/input-request event counts.
    """
    if not session_event_files:
        return _skip(
            "zero_owner_prompts",
            "no session event files were extracted for this trial; cannot prove absence",
        )

    hits: list[dict[str, Any]] = []
    scanned = 0
    for path in session_event_files:
        if not path.is_file():
            continue
        scanned += 1
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                name = str(event.get("event", ""))
            except json.JSONDecodeError:
                m = _EVENT_LINE_RE.search(line)
                name = m.group(1) if m else ""
            lowered = name.lower()
            if any(marker in lowered for marker in APPROVAL_EVENT_MARKERS):
                hits.append({"file": str(path), "line": lineno, "event": name})

    if scanned == 0:
        return _skip(
            "zero_owner_prompts",
            "extracted session-event paths did not resolve to real files",
        )
    if hits:
        return _fail(
            "zero_owner_prompts",
            f"{len(hits)} owner-facing prompt/approval event(s) found across {scanned} session file(s)",
            hits=hits,
        )
    return _pass(
        "zero_owner_prompts",
        f"no owner-facing prompt/approval events found across {scanned} session file(s)",
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_all_checks(
    *,
    scenario: int,
    rows_by_phase: dict[str, Path],
    answer_key: dict[str, Any],
    target_repo_by_phase: dict[str, Path],
    tracker_items_by_phase: dict[str, Path],
    session_event_files: list[Path],
    done_md_path: Path | None = None,
) -> dict[str, Any]:
    """Run the full set of programmatic checks relevant to `scenario`.

    All `*_by_phase` dicts are keyed by phase name (e.g. "main", "drifted")
    in the order the harness ran them. Loading is done here (not by the
    caller) so a malformed rows.yaml/tracker-items file fails loud with the
    exact path in the error, exactly once, in one place.
    """
    loaded_rows: dict[str, list[dict[str, Any]]] = {
        phase: load_rows(path) for phase, path in rows_by_phase.items()
    }
    loaded_tracker: dict[str, list[dict[str, Any]]] = {
        phase: load_tracker_items(path)
        for phase, path in tracker_items_by_phase.items()
    }
    last_phase = list(loaded_rows)[-1] if loaded_rows else None
    last_rows = loaded_rows.get(last_phase, []) if last_phase else []
    last_repo_root = target_repo_by_phase.get(last_phase) if last_phase else None
    last_tracker = loaded_tracker.get(last_phase, []) if last_phase else []

    results: list[CheckResult] = []

    if last_repo_root is not None:
        results.append(check_quote_bytematch(last_rows, last_repo_root))
    else:
        results.append(
            _skip(
                "quote_bytematch",
                "no target-repo snapshot extracted for the last phase",
            )
        )

    results.append(check_coverage(last_rows, answer_key))
    results.append(check_row_tracker_backrefs(last_rows, last_tracker))

    # Data-driven, not scenario-number-gated: each check looks at what the
    # NORMALIZED answer key actually contains and skips honestly if a given
    # fixture doesn't populate that block, rather than assuming which
    # scenario number implies which checks. This held up better than a
    # scenario==N gate once the real fixtures landed with a richer, more
    # varied shape per scenario than originally assumed (see README.md
    # "Interface assumptions" / graders/programmatic.py module docstring).
    results.append(check_planted_findings_caught(loaded_rows, answer_key))
    results.append(check_idempotent_rerun(loaded_rows, answer_key))
    results.append(check_broken_kit_not_conforms(last_rows, answer_key))

    done_md_text = (
        done_md_path.read_text(encoding="utf-8", errors="replace")
        if done_md_path is not None and done_md_path.is_file()
        else None
    )
    results.append(check_false_claim_not_evidence(last_rows, answer_key, done_md_text))

    results.append(check_zero_owner_prompts(session_event_files))

    failed = [r for r in results if r.status == "fail"]
    skipped = [r for r in results if r.status == "skipped"]
    return {
        "scenario": scenario,
        "passed": len(failed) == 0,
        "checks": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "passed": len(results) - len(failed) - len(skipped),
            "failed": len(failed),
            "skipped": len(skipped),
        },
    }


# ---------------------------------------------------------------------------
# Standalone CLI (used for the dry-run verification, and for ad-hoc
# re-grading of an already-extracted trial directory without re-running it)
# ---------------------------------------------------------------------------


def _parse_kv_paths(pairs: list[str] | None) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise argparse.ArgumentTypeError(f"expected PHASE=PATH, got {pair!r}")
        phase, raw_path = pair.split("=", 1)
        out[phase] = Path(raw_path)
    return out


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Standalone runner for the ratchet eval's programmatic checks.",
    )
    ap.add_argument("--scenario", type=int, required=True, choices=[1, 2, 3])
    ap.add_argument("--answer-key", type=Path, required=True)
    ap.add_argument(
        "--rows",
        action="append",
        metavar="PHASE=PATH",
        help="repeatable; e.g. main=rows-main.yaml",
    )
    ap.add_argument(
        "--target-repo",
        action="append",
        metavar="PHASE=PATH",
        help="repeatable; snapshot dir root per phase",
    )
    ap.add_argument(
        "--tracker-items",
        action="append",
        metavar="PHASE=PATH",
        help="repeatable; JSON tracker-list output per phase",
    )
    ap.add_argument("--session-events", nargs="*", default=[], type=Path)
    ap.add_argument("--done-md", type=Path, default=None)
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="write JSON report here (default: stdout)",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        answer_key = load_answer_key(args.answer_key)
        report = run_all_checks(
            scenario=args.scenario,
            rows_by_phase=_parse_kv_paths(args.rows),
            answer_key=answer_key,
            target_repo_by_phase=_parse_kv_paths(args.target_repo),
            tracker_items_by_phase=_parse_kv_paths(args.tracker_items),
            session_event_files=list(args.session_events),
            done_md_path=args.done_md,
        )
    except (AnswerKeyError, FileNotFoundError) as exc:
        print(f"FAIL LOUD: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(report, indent=2, default=str)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
