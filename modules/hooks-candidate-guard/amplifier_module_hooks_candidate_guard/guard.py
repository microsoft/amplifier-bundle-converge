"""Pure guard logic for the candidate-guard hook.

Everything in this module is synchronous and coordinator-free so it can be
unit tested directly (see ``tests/test_guard.py``) without mocking a live
Amplifier session. The only I/O is reading small text files from disk
(the guarded contract file itself, sibling ``CANDIDATE-*.md`` files, and the
optional emergency-unlock token file) -- all funneled through
``_read_file_text`` so tests can monkeypatch a single seam to simulate I/O
failure (see spec Test Plan U8, fail-closed).

Implements the decision order from
``docs/design/hooks-candidate-guard-spec.md`` §4 exactly:

1. ``not config.enabled`` -> continue.
2. ``bash`` scan (self-contained branch, §2.4).
3. ``tool_name`` not in (intercept_tools | tool_name_aliases) -> continue.
4. Extract paths (§2.3), normalized repo-relative against cwd.
5. ``always_allow_globs`` (CANDIDATE-*.md) beats guarding -- checked first.
6. Guarded-path determination (§2.5): glob match AND (optionally) the
   FROZEN/RATIFIED marker actually present in the file's current content.
7. Escape hatch (§2.7) per guarded path: ratified-CANDIDATE (primary) or
   emergency-unlock token (fallback, config-gated).
8. Otherwise -> deny (§2.6).
9. Any exception while evaluating a ``guarded_globs``-matching path fails
   closed (§2.8); errors on non-matching paths are swallowed (continue).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from amplifier_core import HookResult

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class GuardConfig:
    """Configuration surface -- see spec §2.5, §2.7, §3.1 for the defaults.

    Every field is independently overridable by a target repo via the hook's
    ``config:`` block in ``bundle.md`` (mechanism-not-policy, spec §2.5).
    """

    enabled: bool = True

    # §2.5 guarded-path determination
    guarded_globs: list[str] = field(
        default_factory=lambda: [
            "contracts/*.md",
            "contracts/**/*.md",
            "docs/VISION.md",
            "VISION.md",
        ]
    )
    require_frozen_marker: bool = True
    frozen_marker_regex: str = (
        r"(?im)^\*\*Status:\*\*\s*(?:RATIFIED|FROZEN)|^status:\s*FROZEN"
    )
    always_allow_globs: list[str] = field(default_factory=lambda: ["**/CANDIDATE-*.md"])

    # §2.3 tools intercepted + path extraction
    intercept_tools: list[str] = field(
        default_factory=lambda: ["write_file", "edit_file", "apply_patch"]
    )
    tool_name_aliases: list[str] = field(
        default_factory=lambda: ["Write", "Edit", "MultiEdit"]
    )
    path_fields: list[str] = field(default_factory=lambda: ["file_path", "path"])

    # §2.4 bash laundering scan
    scan_bash: bool = True
    bash_tool_name: str = "bash"
    bash_write_patterns: list[str] = field(
        default_factory=lambda: [
            # output redirection: >, >> (also catches heredoc-then-redirect,
            # e.g. `cat <<EOF > guarded.md`, since the `>` still appears).
            r"(?:^|[\s;&|(])\d*>{1,2}\s*([^\s|&;)]+)",
            # tee [-a] <path>
            r"\btee\b(?:\s+-a)?\s+([^\s|&;]+)",
            # dd ... of=<path>
            r"\bdd\b[^|&;]*\bof=([^\s|&;]+)",
            # truncate ... <path>  (path is the trailing token)
            r"\btruncate\b[^|&;]*?\s([^\s|&;]+)\s*(?:[;&|]|$)",
            # cp/mv <src> <dst> -- best-effort: captures the destination
            # token for the common two-argument invocation.
            r"\b(?:cp|mv)\b(?:\s+-\S+)*\s+\S+\s+([^\s|&;]+)",
            # sed -i ... <path> -- best-effort: the in-place target is
            # conventionally the trailing token.
            r"\bsed\b.*-i\S*.*\s([^\s|&;'\"]+)\s*$",
        ]
    )

    # §2.7 escape hatch
    escape_mode: str = "ratified_candidate"  # ratified_candidate | token | both
    candidate_glob: list[str] = field(default_factory=lambda: ["**/CANDIDATE-*.md"])
    ratified_stamp_regex: str = r"(?im)^ratified(?:\s+as\s+edited)?\b.*\bby\s+owner\b"
    candidate_target_field: str = "target"
    allow_emergency_unlock: bool = False
    # Path (relative to cwd) of the git-tracked break-glass token file. See
    # spec §2.7 FALLBACK: a flat `file:` / `reason:` / `by:` text file, only
    # honored when allow_emergency_unlock is True.
    emergency_unlock_token: str = ".converge/UNLOCK"

    # §2.8 fail-closed on internal error
    fail_closed_on_error: bool = True

    # §4.6 rule (b), ENCODE-before-implement -- opt-in, off by default
    enforce_encode_before_impl: bool = False
    encode_marker_path: str = ".converge/encoded"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> GuardConfig:
        """Build a GuardConfig from a plain config dict, ignoring unknown keys.

        Filtering to known dataclass fields prevents a TypeError on an
        unrecognized YAML key (same defensive pattern as
        hooks-process-guard's mount()).
        """
        data = data or {}
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Decision result
# ---------------------------------------------------------------------------


@dataclass
class GuardDecision:
    """A HookResult plus any observability events the caller should emit.

    Keeping event emission out of the pure evaluation path is what makes
    ``evaluate_tool_pre`` and ``evaluate_bash`` fully synchronous and
    coordinator-free; the async mount()-side handler awaits
    ``coordinator.hooks.emit(name, payload)`` for each entry in ``events``.
    """

    result: HookResult
    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Glob matching (supports ** across path segments; stdlib-only)
# ---------------------------------------------------------------------------


def _translate_glob(pattern: str) -> re.Pattern[str]:
    """Translate a gitignore/pathlib-style glob (with ``**`` support) to a
    compiled, fully-anchored regex.

    - ``**/`` (or a bare ``**`` segment) matches zero or more path segments.
    - ``*`` matches any run of characters except ``/``.
    - ``?`` matches a single character except ``/``.
    - Everything else is matched literally.

    Python's stdlib ``fnmatch``/``pathlib.PurePath.match`` don't give us this
    (fnmatch's ``*`` crosses ``/`` freely; ``Path.match`` doesn't support
    ``**`` mid-pattern the way callers here need), so this is a small
    hand-rolled translator rather than a dependency.
    """
    i = 0
    n = len(pattern)
    out: list[str] = []
    while i < n:
        c = pattern[i]
        if c == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                i += 2
                if i < n and pattern[i] == "/":
                    i += 1
                    out.append("(?:.*/)?")
                else:
                    out.append(".*")
            else:
                i += 1
                out.append("[^/]*")
        elif c == "?":
            i += 1
            out.append("[^/]")
        else:
            i += 1
            out.append(re.escape(c))
    return re.compile("^" + "".join(out) + "$")


_GLOB_CACHE: dict[str, re.Pattern[str]] = {}


def _compiled_glob(pattern: str) -> re.Pattern[str]:
    compiled = _GLOB_CACHE.get(pattern)
    if compiled is None:
        compiled = _translate_glob(pattern)
        _GLOB_CACHE[pattern] = compiled
    return compiled


def _glob_match_any(rel_path: str, patterns: list[str]) -> bool:
    return any(_compiled_glob(p).match(rel_path) for p in patterns)


# ---------------------------------------------------------------------------
# Path normalization (within-cwd invariant, spec §2.3)
# ---------------------------------------------------------------------------


def normalize_repo_relative(raw_path: str, cwd: str) -> str | None:
    """Normalize ``raw_path`` to a repo-relative (posix-separated) path.

    Returns ``None`` if the path resolves outside ``cwd`` -- out of scope
    for this hook (spec §2.3 / Test Plan U9); the within-cwd invariant is
    owned elsewhere (the reconciler / recipe layer).
    """
    if not raw_path:
        return None
    try:
        if Path(raw_path).is_absolute():
            abs_path = Path(raw_path)
        else:
            abs_path = Path(cwd) / raw_path
        abs_str = str(abs_path.resolve()) if False else _abspath(abs_path)
        rel = _relpath(abs_str, cwd)
    except (OSError, ValueError):
        return None
    if rel.startswith("..") or Path(rel).is_absolute():
        return None
    return rel.replace("\\", "/")


def _abspath(p: Path) -> str:
    import os

    return os.path.abspath(str(p))


def _relpath(path: str, start: str) -> str:
    import os

    return os.path.relpath(path, start)


# ---------------------------------------------------------------------------
# V4A / unified-diff multi-file marker extraction (spec §2.3)
# ---------------------------------------------------------------------------

_V4A_MARKER_RE = re.compile(r"^\*\*\* (?:Update|Add|Delete) File: (.+)$", re.MULTILINE)
_UNIFIED_DIFF_RE = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def _extract_v4a_markers(body: str) -> list[str]:
    paths = [m.group(1).strip() for m in _V4A_MARKER_RE.finditer(body)]
    paths.extend(m.group(1).strip() for m in _UNIFIED_DIFF_RE.finditer(body))
    return paths


# ---------------------------------------------------------------------------
# Path extraction per tool (spec §2.3)
# ---------------------------------------------------------------------------


def extract_paths(
    tool_name: str, tool_input: dict[str, Any], config: GuardConfig
) -> list[str]:
    """Return every path a given tool call would write to.

    T2 (confirmed live against the composed tool sources -- see module
    README "T2 confirmation" section):
      - write_file / edit_file: ``tool_input["file_path"]`` (native tools;
        ``path_fields`` fallback list covers a CC-named composition too).
      - apply_patch (native engine, the bundle's default composition):
        ``tool_input["path"]`` + ``tool_input["diff"]`` -- one file per
        call; the "diff" field never carries V4A envelope markers for this
        engine (the tool itself rejects them). Scanned anyway, harmlessly,
        for defense in depth.
      - apply_patch (function engine, opt-in via that tool's own config):
        ``tool_input["patch"]`` -- a full V4A envelope that CAN name
        multiple files via ``*** Update File: <path>`` / ``*** Add File:
        <path>`` / ``*** Delete File: <path>`` markers. This is where a
        genuine multi-file patch is detected (spec §2.3, Test Plan U6).
    """
    if tool_name == "apply_patch":
        paths: list[str] = []
        v = tool_input.get("path")
        if isinstance(v, str) and v:
            paths.append(v)
        for body_field in ("diff", "patch"):
            body = tool_input.get(body_field)
            if isinstance(body, str) and body:
                paths.extend(_extract_v4a_markers(body))
        return paths

    direct_field_tools = set(config.intercept_tools) | set(config.tool_name_aliases)
    if tool_name in direct_field_tools:
        for f in config.path_fields:
            v = tool_input.get(f)
            if isinstance(v, str) and v:
                return [v]
        return []

    return []


# ---------------------------------------------------------------------------
# Frozen-marker / guarded-path check (fail-closed seam is _read_file_text)
# ---------------------------------------------------------------------------


def _read_file_text(path: Path) -> str:
    """Read a small text file. Isolated as its own function so tests can
    monkeypatch this single seam to simulate an I/O failure (spec §2.8,
    Test Plan U8)."""
    return path.read_text(encoding="utf-8")


def _is_guarded(rel: str, config: GuardConfig, cwd: str) -> bool:
    """Caller has already confirmed ``rel`` matches ``guarded_globs``.

    Returns True iff the file's *current* on-disk content carries the
    FROZEN/RATIFIED marker (or ``require_frozen_marker`` is disabled, in
    which case glob membership alone is sufficient). May raise -- callers
    are responsible for the fail-closed/continue split described in §2.8.
    """
    if not config.require_frozen_marker:
        return True
    abs_path = Path(cwd) / rel
    if not abs_path.is_file():
        # Doesn't exist yet (a new file under a guarded glob) -- can't
        # already be FROZEN, so this is a create, not a frozen-file amendment.
        return False
    content = _read_file_text(abs_path)
    return bool(re.search(config.frozen_marker_regex, content))


# ---------------------------------------------------------------------------
# Escape hatch (spec §2.7)
# ---------------------------------------------------------------------------


def _extract_field(content: str, field_name: str) -> str | None:
    pattern = rf"(?im)^{re.escape(field_name)}:\s*(.+?)\s*$"
    m = re.search(pattern, content)
    if not m:
        return None
    value = m.group(1).strip().strip("'\"")
    return value or None


def _find_ratified_candidate(rel: str, cwd: str, config: GuardConfig) -> str | None:
    """Search cwd for a CANDIDATE-*.md whose `target:` names ``rel`` and
    whose content carries the ratified stamp. Returns the candidate's
    repo-relative path, or None."""
    root = Path(cwd)
    seen: set[Path] = set()
    for pattern in config.candidate_glob:
        try:
            matches = list(root.glob(pattern))
        except (OSError, ValueError):
            continue
        for candidate_path in matches:
            if candidate_path in seen or not candidate_path.is_file():
                continue
            seen.add(candidate_path)
            try:
                content = _read_file_text(candidate_path)
            except OSError:
                continue
            target = _extract_field(content, config.candidate_target_field)
            if target is None:
                continue
            target_rel = normalize_repo_relative(target, cwd)
            if target_rel != rel:
                continue
            if re.search(config.ratified_stamp_regex, content):
                try:
                    return str(candidate_path.relative_to(root))
                except ValueError:
                    return str(candidate_path)
    return None


def _check_emergency_unlock(rel: str, cwd: str, config: GuardConfig) -> str | None:
    """Break-glass fallback (spec §2.7 FALLBACK). Returns a human-readable
    detail string (for the emitted event) if the token unlocks ``rel``."""
    if not config.allow_emergency_unlock:
        return None
    token_path = Path(cwd) / config.emergency_unlock_token
    if not token_path.is_file():
        return None
    try:
        content = _read_file_text(token_path)
    except OSError:
        return None
    file_field = _extract_field(content, "file")
    if file_field is None:
        return None
    target_rel = normalize_repo_relative(file_field, cwd)
    if target_rel != rel:
        return None
    reason_field = _extract_field(content, "reason") or ""
    by_field = _extract_field(content, "by") or ""
    return f"{config.emergency_unlock_token} (reason={reason_field!r}, by={by_field!r})"


def _check_escape_hatch(
    rel: str, config: GuardConfig, cwd: str
) -> tuple[str, str] | None:
    """Returns (kind, detail) where kind is "ratified" or "token", or None
    if no escape hatch validates for ``rel``."""
    mode = config.escape_mode
    if mode in ("ratified_candidate", "both"):
        candidate = _find_ratified_candidate(rel, cwd, config)
        if candidate is not None:
            return ("ratified", candidate)
    if mode in ("token", "both"):
        unlock = _check_emergency_unlock(rel, cwd, config)
        if unlock is not None:
            return ("token", unlock)
    return None


# ---------------------------------------------------------------------------
# Block message (spec §2.6 -- exact shape)
# ---------------------------------------------------------------------------


def _deny_result(paths: list[str], *, via_shell: bool) -> HookResult:
    rel_path = ", ".join(paths)
    via = " via shell" if via_shell else ""
    reason = (
        f"converge/candidate-guard: BLOCKED direct write{via} to FROZEN file "
        f"'{rel_path}'.\n"
        "PROTOCOL.md §5 (pillar 3): amendments to a frozen vision/contract are "
        "CANDIDATE artifacts, never direct edits.\n"
        "Remedy: author a sibling 'CANDIDATE-<topic>.md' (exact diff · evidence · "
        '"what does NOT change" · ratification ask); the OWNER ratifies with the '
        "literal word ('ratified' / 'ratified as edited' / declined-with-reason). "
        "On ratification the edit lands via the escape hatch (see the module "
        "README / spec §2.7)."
    )
    user_message = (
        f"Blocked direct edit of frozen {rel_path} — use CANDIDATE-<topic>.md "
        "(PROTOCOL.md §5)."
    )
    return HookResult(
        action="deny",
        reason=reason,
        user_message=user_message,
        user_message_level="error",
    )


# ---------------------------------------------------------------------------
# Rule (b) ENCODE-before-implement -- opt-in, off by default (spec §4.6)
# ---------------------------------------------------------------------------


def _check_encode_gate(
    raw_paths: list[str], config: GuardConfig, cwd: str
) -> HookResult | None:
    """Best-effort, coarse phase gate. Honest limit (spec §4.6): this only
    approximates "ENCODE committed" via a marker file; it is not a
    substitute for rule (a), which carries the real guarantee."""
    marker = Path(cwd) / config.encode_marker_path
    if marker.exists():
        return None
    for raw in raw_paths:
        rel = normalize_repo_relative(raw, cwd)
        if rel is None:
            continue
        if rel.endswith(".md"):
            continue  # docs are exempt
        p = Path(rel)
        if "tests" in p.parts or "test" in p.parts or p.name.startswith("test_"):
            continue  # tests are exempt
        return HookResult(
            action="deny",
            reason=(
                f"converge/candidate-guard: BLOCKED implementation write to '{rel}' — "
                f"ENCODE phase marker '{config.encode_marker_path}' is absent "
                "(PROTOCOL.md §4 Phase 2: ENCODE-before-implement). This is an "
                "opt-in, best-effort phase gate (enforce_encode_before_impl); "
                "set it false to disable."
            ),
            user_message=(
                f"Blocked implementation write to {rel} — ENCODE not yet committed."
            ),
            user_message_level="error",
        )
    return None


# ---------------------------------------------------------------------------
# bash laundering scan (spec §2.4)
# ---------------------------------------------------------------------------


def _scan_bash_candidates(command: str, config: GuardConfig) -> list[str]:
    candidates: list[str] = []
    for pattern in config.bash_write_patterns:
        try:
            regex = re.compile(pattern, re.MULTILINE)
        except re.error:
            continue
        for m in regex.finditer(command):
            if m.groups():
                candidates.append(m.group(1))
    return candidates


def _evaluate_bash(
    tool_input: dict[str, Any], config: GuardConfig, cwd: str
) -> GuardDecision:
    command = tool_input.get("command", "")
    if not isinstance(command, str) or not command:
        return GuardDecision(HookResult(action="continue"))

    candidates = _scan_bash_candidates(command, config)
    guarded_hits: list[str] = []
    for raw in candidates:
        rel = normalize_repo_relative(raw, cwd)
        if rel is None:
            continue
        if _glob_match_any(rel, config.always_allow_globs):
            continue
        if not _glob_match_any(rel, config.guarded_globs):
            continue
        try:
            if _is_guarded(rel, config, cwd):
                guarded_hits.append(rel)
        except Exception:  # noqa: BLE001 -- deliberate: fail-closed per spec §2.8
            if config.fail_closed_on_error:
                guarded_hits.append(rel)
            # else: swallow and treat as not-guarded (continue) for this hit.

    if not guarded_hits:
        return GuardDecision(HookResult(action="continue"))

    result = _deny_result(guarded_hits, via_shell=True)
    events = [
        (
            "converge:guard_blocked",
            {
                "path": p,
                "tool": config.bash_tool_name,
                "reason_code": "frozen_bash_write",
            },
        )
        for p in guarded_hits
    ]
    return GuardDecision(result, events)


# ---------------------------------------------------------------------------
# Main entry point (spec §4, decision order)
# ---------------------------------------------------------------------------


def evaluate_tool_pre(
    tool_name: str,
    tool_input: dict[str, Any],
    config: GuardConfig,
    cwd: str,
) -> GuardDecision:
    """Evaluate a single ``tool:pre`` event and return the guard's decision.

    Pure function: no coordinator, no async. See module docstring for the
    decision order (mirrors spec §4 step-for-step).
    """
    # Step 1
    if not config.enabled:
        return GuardDecision(HookResult(action="continue"))

    # Step 2 -- bash is a self-contained branch (§2.4)
    if tool_name == config.bash_tool_name and config.scan_bash:
        return _evaluate_bash(tool_input, config, cwd)

    # Step 3
    direct_field_tools = set(config.intercept_tools) | set(config.tool_name_aliases)
    if tool_name not in direct_field_tools and tool_name != "apply_patch":
        return GuardDecision(HookResult(action="continue"))

    # Step 4
    raw_paths = extract_paths(tool_name, tool_input, config)
    if not raw_paths:
        return GuardDecision(HookResult(action="continue"))

    guarded_paths: list[str] = []
    for raw in raw_paths:
        rel = normalize_repo_relative(raw, cwd)
        if rel is None:
            # Step 9 (partial): outside cwd is out of this hook's scope (U9)
            continue

        # Step 5 -- always-allow (CANDIDATE) beats guarding, checked first
        if _glob_match_any(rel, config.always_allow_globs):
            continue

        # Step 6 -- guarded-path determination, with fail-closed on error
        if not _glob_match_any(rel, config.guarded_globs):
            continue
        try:
            guarded = _is_guarded(rel, config, cwd)
        except Exception as exc:  # noqa: BLE001 -- deliberate: fail-closed per spec §2.8
            if config.fail_closed_on_error:
                return GuardDecision(
                    HookResult(
                        action="deny",
                        reason=(
                            f"converge/candidate-guard: guard evaluation error for "
                            f"'{rel}': {exc}. Failing closed (spec §2.8)."
                        ),
                        user_message=(
                            f"Guard evaluation error for {rel} — failing closed."
                        ),
                        user_message_level="error",
                    )
                )
            continue
        if guarded:
            guarded_paths.append(rel)

    if not guarded_paths:
        if config.enforce_encode_before_impl:
            gate_result = _check_encode_gate(raw_paths, config, cwd)
            if gate_result is not None:
                return GuardDecision(gate_result)
        return GuardDecision(HookResult(action="continue"))

    # Step 7/8 -- escape hatch per guarded path; deny if any lacks one
    events: list[tuple[str, dict[str, Any]]] = []
    blocked: list[str] = []
    for rel in guarded_paths:
        escape = _check_escape_hatch(rel, config, cwd)
        if escape is None:
            blocked.append(rel)
        else:
            kind, detail = escape
            if kind == "ratified":
                events.append(
                    (
                        "converge:guard_allowed_ratified",
                        {"path": rel, "candidate": detail},
                    )
                )
            else:
                events.append(
                    ("converge:guard_unlock_used", {"path": rel, "token": detail})
                )

    if blocked:
        result = _deny_result(blocked, via_shell=False)
        blocked_events = [
            (
                "converge:guard_blocked",
                {"path": p, "tool": tool_name, "reason_code": "frozen_direct_edit"},
            )
            for p in blocked
        ]
        return GuardDecision(result, blocked_events)

    return GuardDecision(HookResult(action="continue"), events)
