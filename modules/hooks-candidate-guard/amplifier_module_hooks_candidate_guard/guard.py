"""Pure guard logic for the candidate-guard hook.

Everything in this module is synchronous and coordinator-free so it can be
unit tested directly (see ``tests/test_guard.py``) without mocking a live
Amplifier session. The only I/O is reading small text files from disk
(the guarded contract file itself, sibling proposal files under either
sanctioned name -- ``<contract>.vN-candidate.md`` or the legacy
``CANDIDATE-*.md`` -- and the optional emergency-unlock token file), all
funneled through
``_read_file_text`` so tests can monkeypatch a single seam to simulate I/O
failure (see spec Test Plan U8, fail-closed).

Implements the decision order from
``docs/design/hooks-candidate-guard-spec.md`` §4 exactly:

1. ``not config.enabled`` -> continue.
2. ``bash`` scan (self-contained branch, §2.4).
3. ``tool_name`` not in (intercept_tools | tool_name_aliases) -> continue.
4. Extract paths (§2.3), resolved against the GOVERNING repository root --
   the nearest ancestor of the target that carries a ``.git`` entry, bounded
   at cwd (converge-qfi9). A repo that sits BELOW the session cwd is guarded
   by its own layout; the within-cwd invariant is unchanged, so a path
   outside cwd is still out of scope.
5. ``always_allow_globs`` (both proposal names -- see ``PROPOSAL_GLOBS``)
   beats guarding -- checked first.
6. Guarded-path determination (§2.5): glob match AND (optionally) the
   FROZEN/RATIFIED marker actually present in the file's current content.
6b. The half-freeze check (converge-p17d), for a matching path that is NOT
   yet locked: a write may not leave the document locked unless that same
   write also adds the line recording the lock. Refused before anything is
   written, so the document stays a draft and the combined write can be
   re-issued.
7. Escape hatch (§2.7) per guarded path: ratified-CANDIDATE (primary) or
   emergency-unlock token (fallback, config-gated). A ratified candidate
   already recorded in the target's own Changelog -- matched as a complete
   path token, never a substring or bare basename -- is spent and does not
   count (converge-wu3y, single-use); the search continues to any other
   candidate for the same target. The already-landed check reuses the
   target's content read in step 6 rather than reading it a second time.
8. Otherwise -> deny (§2.6).
9. Any exception while evaluating a ``guarded_globs``-matching path --
   including one raised while checking the escape hatch in step 7 -- fails
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


# The two sanctioned proposal filenames, in preference order. A proposal is
# `<contract>.vN-candidate.md` (contracts/documents.v1 clause 8); the legacy
# `CANDIDATE-<topic>.md` from PROTOCOL.md §5 is still admitted so repos written
# against the older name keep working. Both are the ONLY writes sanctioned
# beside a locked (FROZEN) contract -- composition.v1 clause 7.
PROPOSAL_GLOBS: list[str] = [
    "**/*.v[0-9]*-candidate.md",
    "**/CANDIDATE-*.md",
]


@dataclass
class GuardConfig:
    """Configuration surface -- see spec §2.5, §2.7, §3.1 for the defaults.

    Every field is independently overridable by a target repo via the hook's
    ``config:`` block in ``bundle.md`` (mechanism-not-policy, spec §2.5).
    """

    enabled: bool = True

    # §2.5 guarded-path determination
    # `docs/PROTOCOL.md` / `PROTOCOL.md` sit here beside VISION for the same
    # reason (converge-dwi): the protocol is a ratified document that changes
    # by proposal, and it carries its status in the H1 exactly as a contract
    # does. Both spellings are listed for the same reason both VISION
    # spellings are -- a repo may keep either at its root or under docs/.
    # A file only becomes guarded when its content actually carries a locked
    # marker, so listing a path that is still DRAFT costs nothing.
    guarded_globs: list[str] = field(
        default_factory=lambda: [
            "contracts/*.md",
            "contracts/**/*.md",
            "docs/VISION.md",
            "VISION.md",
            "docs/PROTOCOL.md",
            "PROTOCOL.md",
        ]
    )
    require_frozen_marker: bool = True
    # THREE locked-marker forms, in one alternation. Byte-identical to the
    # shipped `frozen_marker_regex` in behaviors/converge.yaml -- if you change
    # one, change the other, or a repo on module defaults and a repo on the
    # shipped config disagree about what "locked" means.
    #
    #   ^#.*\((?:FROZEN|RATIFIED)\b
    #                         the ratified anatomy: contracts/documents.v1
    #                         clause 6 -- "status lives in the H1 parenthetical
    #                         and nowhere else", e.g.
    #                         `# Documents Contract - v1 (FROZEN 2026-09-02)`.
    #                         `(FROZEN` is the form .githooks/pre-push checks.
    #                         `(RATIFIED` is admitted for the same reason the
    #                         BODY branch below already admits
    #                         `**Status:** RATIFIED` (converge-dwi): the two
    #                         branches disagreeing about one word meant the
    #                         SAME status word read as LOCKED in the body and
    #                         UNLOCKED in the H1 -- and moving status into the
    #                         H1 is exactly what clause 6 mandates.
    #                         docs/PROTOCOL.md is the live instance: its H1
    #                         reads `... Protocol v3 (RATIFIED 2026-09-03)`
    #                         and it carries no body status line at all.
    #   **Status:** ...       legacy body marker, still honored so a repo that
    #   status: FROZEN        locked a contract under the older convention does
    #                         not silently become writable on upgrade.
    #
    # Deliberately loose on the H1 branch (any `#`-led line, case-insensitive):
    # over-matching only ever guards MORE, and a guard that under-matches fails
    # silently. Proposal files that quote a locked H1 are unaffected --
    # always_allow_globs is checked first (decision order step 5).
    frozen_marker_regex: str = (
        r"(?im)^\*\*Status:\*\*\s*(?:RATIFIED|FROZEN)|^status:\s*FROZEN"
        r"|^#.*\((?:FROZEN|RATIFIED)\b"
    )
    always_allow_globs: list[str] = field(default_factory=lambda: list(PROPOSAL_GLOBS))

    # The half-freeze check (converge-p17d). A document is locked by editing
    # its own H1, and the record of that lock is more text in the SAME file.
    # Done in two edits, the first one lands the status word and the second is
    # refused by the branch above -- because by then the file reads locked. The
    # document is left half-frozen and no later edit can repair it.
    #
    # So: a write may not LEAVE a guarded document locked unless that same
    # write also adds the line recording the lock. The promise above is
    # untouched -- a locked document still takes no content edit, ever. What
    # changes is that the half-frozen state stops being reachable, rather than
    # becoming writable. The refusal happens BEFORE anything is written, so the
    # document is still a draft and the combined write can just be re-issued.
    require_lock_record: bool = True
    # What counts as the record: a non-heading line naming a locking word. The
    # status stamp itself never counts (it is what is being recorded), and
    # neither does a line already on disk -- the record has to be one THIS
    # write adds, or an older version's changelog entry would satisfy it by
    # accident.
    lock_record_regex: str = r"(?im)^(?!\s*#).*\b(?:FROZEN|RATIFIED|LOCKED)\b"

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
    candidate_glob: list[str] = field(default_factory=lambda: list(PROPOSAL_GLOBS))
    ratified_stamp_regex: str = r"(?im)^ratified(?:\s+as\s+edited)?\b.*\bby\s+owner\b"
    candidate_target_field: str = "target"
    allow_emergency_unlock: bool = False
    # Path of the git-tracked break-glass token file, relative to the guarded
    # document's own governing repository root (converge-qfi9) -- the same
    # frame its `file:` line is read in. See
    # spec §2.7 FALLBACK: a flat `file:` / `reason:` / `by:` text file, only
    # honored when allow_emergency_unlock is True.
    emergency_unlock_token: str = ".converge/UNLOCK"

    # §2.8 fail-closed on internal error
    fail_closed_on_error: bool = True

    # Second write path: direct tool dispatch that never emits `tool:pre`.
    # `amplifier tool invoke <tool> ...` builds a full session (this hook DOES
    # mount and IS registered on tool:pre -- measured) and then calls
    # `tools[name].execute(args)` itself, so no `tool:pre` is ever emitted and
    # NO hook on that event can see the write. With this on (the default), the
    # guard also wraps the mounted tool instances' own `execute`, evaluating
    # the identical pure function, so the deny holds on both paths.
    # See the module README, "The two write paths".
    wrap_tool_execute: bool = True

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
    - ``[...]`` matches one character from the set (ranges and a leading
      ``!``/``^`` negation supported, never crossing ``/``). Needed by the
      shipped ``**/*.v[0-9]*-candidate.md`` proposal glob so that "vN"
      requires an actual digit; an unterminated ``[`` is treated literally.
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
        elif c == "[":
            body, next_i = _scan_char_class(pattern, i)
            if body is None:
                # Unterminated '[' -- literal, matching fnmatch's behavior.
                i += 1
                out.append(re.escape(c))
            else:
                i = next_i
                out.append(body)
        else:
            i += 1
            out.append(re.escape(c))
    return re.compile("^" + "".join(out) + "$")


def _scan_char_class(pattern: str, start: int) -> tuple[str | None, int]:
    """Scan a ``[...]`` class starting at ``start`` (which indexes the ``[``).

    Returns ``(regex_fragment, index_after_class)``, or ``(None, start)`` if
    the class is unterminated. The fragment never matches ``/`` -- a path
    separator can never be swallowed by a character class, mirroring the
    ``*``/``?`` rules above.
    """
    i = start + 1
    n = len(pattern)
    negated = False
    if i < n and pattern[i] in "!^":
        negated = True
        i += 1
    # A ']' immediately after '[' (or after the negation) is a literal ']'.
    body_start = i
    if i < n and pattern[i] == "]":
        i += 1
    while i < n and pattern[i] != "]":
        i += 1
    if i >= n:
        return (None, start)
    raw = pattern[body_start:i]
    if not raw:
        return (None, start)
    # Escape regex metacharacters that are still special inside a class,
    # leaving '-' ranges intact.
    safe = raw.replace("\\", "\\\\").replace("^", "\\^").replace("[", "\\[")
    if negated:
        return (f"[^/{safe}]", i + 1)
    return (f"(?![/])[{safe}]", i + 1)


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

    This is the within-cwd GATE, and it is also how a proposal's ``target:``
    line and the break-glass token's ``file:`` line are read -- in those two
    cases ``cwd`` is passed the governing repository root, so the whole
    decision stays in one frame (see ``resolve_target_path``).
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
# Governing-root resolution (converge-qfi9)
# ---------------------------------------------------------------------------
#
# `guarded_globs` -- `contracts/*.md`, `docs/VISION.md`, `PROTOCOL.md` -- is a
# statement about a REPOSITORY's layout, not about whichever directory a
# session happens to have been started in. Relativizing against the session
# cwd conflated the two: with cwd at a multi-repo workspace root, a FROZEN
# `amplifier-work-tracker/contracts/operator-surface.v1.md` normalized to
# `amplifier-work-tracker/contracts/...`, which matches no shipped glob, and
# three direct edits to a locked contract went through unblocked (measured
# 2026-09-06, three sessions, the module mounted and evaluating throughout).
#
# So a target is resolved in its OWN repository's frame: the nearest ancestor
# carrying a `.git` entry, searched from the file's directory upward and
# bounded at cwd. `.git` is tested with `.exists()`, not `.is_dir()`, because
# in a git worktree (every Converge lane is one) `.git` is a file.
#
# Why not simply ship `**/`-prefixed globs instead (the smaller change): it
# fixes the deny and silently welds the remedy shut. Measured on this same
# fixture -- with `**/contracts/*.md` and cwd at the workspace, a ratified
# `contracts/operator-surface.v2-candidate.md` sitting beside the contract
# no longer opens the escape hatch, because the proposal's `target:` line
# normalizes against cwd while the guarded path does not. A deny with no
# reachable remedy is worse than the bug. Resolving everything -- the guarded
# path, the proposal search, the `target:` line, the break-glass token -- in
# one repository frame keeps the hatch coherent.
#
# Honest limit: a directory below cwd that is not a git repository has no
# repository frame, so it falls back to cwd and is matched as before.


def find_governing_root(abs_path: str, cwd: str) -> str:
    """Return the repository root that governs ``abs_path``.

    Searches from the target's own directory upward for the first ancestor
    containing a ``.git`` entry, stopping at ``cwd``. Falls back to ``cwd``
    when the target is not inside a repository below it -- which is exactly
    the pre-existing behavior, so a session whose cwd IS the repo root is
    unaffected.
    """
    cwd_abs = _abspath(Path(cwd))
    chain: list[str] = []
    current = Path(_abspath(Path(abs_path))).parent
    while True:
        current_abs = _abspath(current)
        chain.append(current_abs)
        if current_abs == cwd_abs:
            break
        parent = current.parent
        if _abspath(parent) == current_abs:
            # Walked to the filesystem root without meeting cwd. The caller's
            # within-cwd check should make this unreachable; fall back rather
            # than search outside cwd.
            return cwd_abs
        current = parent
    for candidate in chain:  # deepest first
        try:
            if (Path(candidate) / ".git").exists():
                return candidate
        except OSError:
            continue
    return cwd_abs


@dataclass(frozen=True)
class TargetPath:
    """A write target, expressed in the two frames the guard needs.

    ``rel`` is the frame every decision is made in -- glob matching, the
    on-disk marker read, the proposal search, the token check. ``display``
    is the frame a human reads: a path they can actually use from the
    session cwd. They are identical whenever cwd IS the repository root.
    """

    root: str  # absolute governing repository root
    rel: str  # target relative to ``root`` (posix) -- what globs match
    display: str  # target relative to cwd (posix) -- what messages/events show


def resolve_target_path(raw_path: str, cwd: str) -> TargetPath | None:
    """Resolve ``raw_path`` to its governing repo frame, or None if out of scope.

    Out of scope means the same thing it has always meant: the path resolves
    outside ``cwd`` (spec §2.3 / Test Plan U9).
    """
    cwd_rel = normalize_repo_relative(raw_path, cwd)
    if cwd_rel is None:
        return None
    try:
        abs_path = _abspath(Path(cwd) / cwd_rel)
        root = find_governing_root(abs_path, cwd)
        rel = _relpath(abs_path, root)
    except (OSError, ValueError):
        return None
    return TargetPath(root=root, rel=rel.replace("\\", "/"), display=cwd_rel)


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


def _read_guarded_content(
    rel: str, config: GuardConfig, root: str
) -> tuple[bool, str | None]:
    """Like ``_is_guarded``, but also returns the content actually read (if
    any), so a caller that goes on to check the escape hatch (converge-wu3y)
    can reuse it instead of reading the same guarded target a SECOND time.

    Returns ``(guarded, content)``. ``content`` is ``None`` when
    ``require_frozen_marker`` is disabled (glob membership alone decided it,
    so nothing was read) or when the file does not exist yet -- in either
    case there is nothing to reuse, and a caller that needs content anyway
    (the escape-hatch's own already-landed check) reads it itself. May
    raise -- callers are responsible for the fail-closed/continue split
    described in §2.8, exactly as before.
    """
    if not config.require_frozen_marker:
        return True, None
    abs_path = Path(root) / rel
    if not abs_path.is_file():
        # Doesn't exist yet (a new file under a guarded glob) -- can't
        # already be FROZEN, so this is a create, not a frozen-file amendment.
        return False, None
    content = _read_file_text(abs_path)
    return bool(re.search(config.frozen_marker_regex, content)), content


def _is_guarded(rel: str, config: GuardConfig, root: str) -> bool:
    """Caller has already confirmed ``rel`` matches ``guarded_globs``.

    Returns True iff the file's *current* on-disk content carries the
    FROZEN/RATIFIED marker (or ``require_frozen_marker`` is disabled, in
    which case glob membership alone is sufficient). May raise -- callers
    are responsible for the fail-closed/continue split described in §2.8.

    Thin wrapper over ``_read_guarded_content`` for callers (the ``bash``
    branch) that have no use for the content itself.
    """
    guarded, _content = _read_guarded_content(rel, config, root)
    return guarded


# ---------------------------------------------------------------------------
# The half-freeze check (converge-p17d)
# ---------------------------------------------------------------------------


def _added_diff_lines(body: str) -> list[str]:
    """The lines a unified / V4A diff body would ADD, with the ``+`` stripped.

    ``+++ b/<path>`` is a file header, not an added line, and is skipped.
    """
    added: list[str] = []
    for line in body.splitlines():
        if line.startswith("+++"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
    return added


def _resulting_content(tool_input: dict[str, Any], before: str) -> str | None:
    """Best-effort reconstruction of what the file would say after this write.

    Keyed on the FIELDS present rather than on the tool name, so a
    differently-named composition of the same tool is read the same way:

      - ``content``                      -> the whole file (write_file / Write)
      - ``old_string`` / ``new_string``  -> the replacement applied to ``before``
                                            (edit_file / Edit / MultiEdit)
      - ``diff`` / ``patch``             -> ``before`` plus the diff's added
                                            lines (apply_patch). Deliberately
                                            additive: a patch is not applied
                                            here, and it does not need to be --
                                            a stamp and a changelog entry are
                                            both ADDED lines.

    Returns None when the write's result cannot be reconstructed at all, which
    the caller treats as "no opinion" rather than as a refusal.
    """
    content = tool_input.get("content")
    if isinstance(content, str):
        return content

    old = tool_input.get("old_string")
    new = tool_input.get("new_string")
    if isinstance(old, str) and isinstance(new, str) and old:
        if tool_input.get("replace_all"):
            return before.replace(old, new)
        return before.replace(old, new, 1)

    added: list[str] = []
    for body_field in ("diff", "patch"):
        body = tool_input.get(body_field)
        if isinstance(body, str) and body:
            added.extend(_added_diff_lines(body))
    if added:
        return before + "\n" + "\n".join(added)

    return None


def _lock_without_record(
    rel: str, tool_input: dict[str, Any], config: GuardConfig, root: str
) -> str | None:
    """Return the locking marker a write would leave UNRECORDED, else None.

    Caller has already established that ``rel`` matches ``guarded_globs`` and
    that the file is NOT currently locked (so the ordinary deny path does not
    own it).

    The honest limit, stated once: this watches the DRAFT -> LOCKED transition
    of a document already on disk. A file that does not exist yet is out of
    scope -- creating one that already carries a locking word is an import or
    a copy, a different act the guard has never had an opinion about. Nor does
    the ``bash`` branch reach here: a shell write's resulting content is not
    knowable from the command line alone.
    """
    abs_path = Path(root) / rel
    if not abs_path.is_file():
        return None
    before = _read_file_text(abs_path)
    if re.search(config.frozen_marker_regex, before):
        return None  # already locked -- §2.6 owns this write, not this check

    after = _resulting_content(tool_input, before)
    if after is None:
        return None
    marker = re.search(config.frozen_marker_regex, after)
    if marker is None:
        return None  # this write does not lock anything

    seen = {line.strip() for line in before.splitlines()}
    for line in after.splitlines():
        text = line.strip()
        if not text or text in seen:
            continue  # already on disk: not a record THIS write adds
        if re.search(config.frozen_marker_regex, line):
            continue  # the status stamp is not its own record
        if re.search(config.lock_record_regex, line):
            return None
    return marker.group(0).strip()


def _lock_record_deny(items: list[tuple[str, str]]) -> HookResult:
    rel_path = ", ".join(rel for rel, _ in items)
    marker = items[0][1] if items else "the locking word"
    day = "2026-09-06"
    found = re.search(r"(\d{4}-\d{2}-\d{2})", marker)
    if found:
        day = found.group(1)
    reason = (
        f"converge/candidate-guard: BLOCKED a write to '{rel_path}' that would "
        f"lock the document without recording the lock.\n"
        f"This write stamps {marker!r} into the file but adds no line recording "
        "that locking, so the document would be left half-frozen: the status "
        "word lands, the record of why it landed does not \u2014 and every later "
        "edit that would add it is refused, because by then the file reads "
        "locked.\n"
        "contracts/documents.v1 Core 6 (status lives in the H1 parenthetical "
        "and nowhere else) and Core 7 (a dated changelog whose entries carry "
        "evidence).\n"
        "Remedy: the freeze is ONE edit, never two. In a single write, stamp "
        "the H1 AND add the Changelog entry that records the ratification \u2014 "
        "for example:\n"
        f"    # <Title> (FROZEN {day})\n"
        "    ...\n"
        "    ## Changelog\n"
        "\n"
        f"    - **{day} \u2014 v1 (FROZEN {day}).** Locked on the steward's word; "
        "the four Freeze Bar conditions are recorded in "
        f"docs/workflow/owner-ratifications-{day}.md.\n"
        "Nothing has been written: the document is still a draft, so re-issue "
        "the two halves as one write."
    )
    user_message = (
        f"Blocked a lock of {rel_path} that carries no record of the locking \u2014 "
        "stamp the H1 and write the Changelog entry in ONE edit."
    )
    return HookResult(
        action="deny",
        reason=reason,
        user_message=user_message,
        user_message_level="error",
    )


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


# ---------------------------------------------------------------------------
# Single-use: a ratified candidate already recorded on its target is spent
# (converge-wu3y)
#
# MEASURED 2026-09-06: `contracts/operator-surface.v2-candidate.md` was
# ratified, applied to the locked target via PR #90, and then left in place
# with its `target:` line unchanged -- so `_find_ratified_candidate` kept
# finding it and the escape hatch stayed open indefinitely for anyone, for as
# long as the applied candidate existed. The README documented single-landing
# as an expectation ("the ratified proposal is expected to be archived"), not
# a mechanism -- an expectation nobody's checklist carries is exactly how it
# was missed.
#
# The rule: a candidate stops unlocking its target once the target's own
# ``## Changelog`` already names it. Landing an amendment always means
# writing a changelog entry (composition.v1 clause 7 / the freeze-bar
# convention this module already enforces via the half-freeze check above),
# so the changelog is the one place "already landed" is recorded, in the same
# file, by the same write that used the hatch. Checking the CANDIDATE'S OWN
# repo-relative path there -- not a date, not a fuzzy substring of the
# proposal's prose -- is the minimum reliable signal: a date or a bare word
# could belong to a different, still-unspent proposal that happens to share
# one; the candidate's path cannot.
# ---------------------------------------------------------------------------


def _changelog_section(content: str) -> str | None:
    """Return the text under the document's own ``## Changelog`` heading
    (any ``#``-level heading spelled "Changelog"), up to the next heading of
    the same or shallower level, or ``None`` if the document carries no such
    section.

    Deliberately narrow: only text actually inside the Changelog counts as a
    record that an amendment landed. A candidate's path appearing elsewhere
    in the document (its own prose, a cross-reference) is not evidence of
    that -- restricting the search to the Changelog is what keeps this from
    becoming exactly the kind of fuzzy match that could close an unrelated,
    still-unspent proposal by accident.
    """
    lines = content.splitlines()
    start: int | None = None
    level = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s*changelog\b", line, re.IGNORECASE)
        if m:
            start = i + 1
            level = len(m.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for i in range(start, len(lines)):
        m = re.match(r"^(#{1,6})\s+\S", lines[i])
        if m and len(m.group(1)) <= level:
            end = i
            break
    return "\n".join(lines[start:end])


_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+")


def _changelog_records_candidate(changelog: str, candidate_rel: str) -> bool:
    """True iff ``candidate_rel`` -- the candidate's own repo-relative path,
    forward-slash normalized -- appears in ``changelog`` as a COMPLETE path
    token, never as a substring of a longer filename and never by bare
    basename (converge-wu3y defect 2: the previous check used
    ``candidate_rel in changelog or candidate_path.name in changelog``, a
    substring-OR-basename test that reads two different documents as "the
    same candidate").

    A token is a maximal run of path-safe characters
    (``[A-Za-z0-9_./-]``); comparing whole tokens instead of doing a raw
    substring search is what tells ``contracts/x.v2-candidate.md`` apart
    from a changelog that only names the longer, different
    ``contracts/x.v2-candidate.md.bak`` (a substring match would wrongly
    accept this: the shorter path is a literal prefix of the longer one),
    and from ``notes/x.v2-candidate.md`` -- a different directory that
    happens to share the same basename (the removed basename fallback would
    wrongly accept this too). Markdown backticks, link parentheses, and
    quoting all fall outside the path-token character class, so they bound
    a token correctly with no special-casing needed for those forms.

    One deliberately narrow normalization: a token that mismatches only
    because it ends in a single extra ``.`` is retried with that one
    trailing dot stripped, so an ordinary end-of-sentence period placed
    directly after the path with no backticks (``...candidate.md.``) is not
    mistaken for part of the filename. This does not reopen the
    ``.bak``-style false positive: ``contracts/x.v2-candidate.md.bak`` does
    not end in ``.`` at all, so nothing is stripped from it and the exact
    comparison still fails.
    """
    for match in _PATH_TOKEN_RE.finditer(changelog):
        token = match.group(0)
        if token == candidate_rel:
            return True
        if token.endswith(".") and token[:-1] == candidate_rel:
            return True
    return False


def _candidate_already_landed(
    root: str,
    rel: str,
    candidate_path: Path,
    target_content: str | None = None,
) -> bool:
    """Return True iff the guarded document's own Changelog already records
    ``candidate_path`` by its repo-relative path -- the amendment is spent,
    and this candidate must not reopen the hatch (converge-wu3y).

    Matches on the candidate's exact repo-relative path (e.g.
    ``contracts/operator-surface.v2-candidate.md``) as a complete path
    token (``_changelog_records_candidate``) -- never a fuzzy substring, a
    bare basename, or a bare date: any of those could belong to a
    different, still-unspent proposal, or to an unrelated longer filename
    that merely starts the same way. The path is the one thing that names
    THIS candidate and no other.

    ``target_content`` is the guarded document's content, when the caller
    (``evaluate_tool_pre``) already read it successfully while determining
    the path was guarded in the first place -- passed through so the target
    is never read a SECOND time (converge-wu3y defect 1: a second read that
    failed was previously swallowed into "not recorded", silently reopening
    the hatch on a transient I/O error despite ``fail_closed_on_error``).
    When it is not supplied (a direct call, or ``require_frozen_marker``
    disabled so nothing was read yet), the content is read here instead;
    unlike the previous version, a failure on THAT read is no longer
    caught and turned into "not recorded" -- it propagates, so the caller's
    own fail-closed policy (spec §2.8) decides the outcome, exactly as any
    other guard-evaluation error. Never silently open a locked file on
    uncertainty.
    """
    if target_content is not None:
        content = target_content
    else:
        abs_path = Path(root) / rel
        if not abs_path.is_file():
            return False
        content = _read_file_text(abs_path)  # let OSError propagate: fail closed
    changelog = _changelog_section(content)
    if not changelog:
        return False
    try:
        candidate_rel = str(candidate_path.relative_to(root))
    except ValueError:
        candidate_rel = candidate_path.name
    candidate_rel = candidate_rel.replace("\\", "/")
    return _changelog_records_candidate(changelog, candidate_rel)


def _find_ratified_candidate(
    rel: str,
    root: str,
    config: GuardConfig,
    target_content: str | None = None,
) -> str | None:
    """Search the guarded document's own repository for a proposal file --
    under either sanctioned name, ``<contract>.vN-candidate.md`` or the legacy
    ``CANDIDATE-*.md`` -- whose ``target:`` names ``rel`` and whose content
    carries the ratified stamp. Returns the proposal's repo-relative path,
    or None.

    The ``target:`` line is required under BOTH names: the guard never infers
    which contract a proposal amends from its filename alone.

    ``root`` is the governing repository root the guarded path was resolved
    against (converge-qfi9), NOT necessarily the session cwd -- so a proposal
    beside a contract in a repo BELOW cwd, carrying the ``target:`` line a
    person in that repo would write, still opens the hatch.

    ``target_content``, when supplied, is forwarded to
    ``_candidate_already_landed`` so the guarded target is never read twice
    (converge-wu3y defect 1) -- see that function's docstring.

    A candidate that matches but whose amendment is already recorded in the
    target's own Changelog (``_candidate_already_landed``) is SKIPPED, not
    returned: it is spent, and the search continues to the next candidate
    file rather than stopping here (a still-unspent candidate for the same
    target, filed after the first one landed, must still open the hatch)."""
    search_root = Path(root)
    seen: set[Path] = set()
    for pattern in config.candidate_glob:
        try:
            matches = list(search_root.glob(pattern))
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
            target_rel = normalize_repo_relative(target, root)
            if target_rel != rel:
                continue
            if not re.search(config.ratified_stamp_regex, content):
                continue
            if _candidate_already_landed(
                root, rel, candidate_path, target_content=target_content
            ):
                continue  # spent -- already recorded, does not reopen the hatch
            try:
                return str(candidate_path.relative_to(search_root))
            except ValueError:
                return str(candidate_path)
    return None


def _check_emergency_unlock(rel: str, root: str, config: GuardConfig) -> str | None:
    """Break-glass fallback (spec §2.7 FALLBACK). Returns a human-readable
    detail string (for the emitted event) if the token unlocks ``rel``."""
    if not config.allow_emergency_unlock:
        return None
    token_path = Path(root) / config.emergency_unlock_token
    if not token_path.is_file():
        return None
    try:
        content = _read_file_text(token_path)
    except OSError:
        return None
    file_field = _extract_field(content, "file")
    if file_field is None:
        return None
    target_rel = normalize_repo_relative(file_field, root)
    if target_rel != rel:
        return None
    reason_field = _extract_field(content, "reason") or ""
    by_field = _extract_field(content, "by") or ""
    return f"{config.emergency_unlock_token} (reason={reason_field!r}, by={by_field!r})"


def _check_escape_hatch(
    rel: str,
    config: GuardConfig,
    root: str,
    target_content: str | None = None,
) -> tuple[str, str] | None:
    """Returns (kind, detail) where kind is "ratified" or "token", or None
    if no escape hatch validates for ``rel``.

    ``target_content``, when supplied, is the guarded target's already-read
    content, forwarded to ``_find_ratified_candidate`` so the single-use
    (converge-wu3y) already-landed check never reads the target a second
    time."""
    mode = config.escape_mode
    if mode in ("ratified_candidate", "both"):
        candidate = _find_ratified_candidate(
            rel, root, config, target_content=target_content
        )
        if candidate is not None:
            return ("ratified", candidate)
    if mode in ("token", "both"):
        unlock = _check_emergency_unlock(rel, root, config)
        if unlock is not None:
            return ("token", unlock)
    return None


# ---------------------------------------------------------------------------
# Block message (spec §2.6 -- exact shape)
# ---------------------------------------------------------------------------


def _proposal_name_for(rel: str) -> str:
    """Suggest the concrete proposal filename for a locked contract path.

    ``contracts/composition.v1.md`` -> ``contracts/composition.v2-candidate.md``.
    Falls back to the generic shape when the path carries no ``vN`` version
    segment (e.g. ``docs/VISION.md``), so the deny message always names a
    real, writable path rather than a template the reader has to decode.
    """
    m = re.match(r"^(?P<stem>.*)\.v(?P<n>\d+)\.md$", rel)
    if m:
        return f"{m.group('stem')}.v{int(m.group('n')) + 1}-candidate.md"
    if rel.endswith(".md"):
        return f"{rel[: -len('.md')]}.v2-candidate.md"
    return "<contract>.vN-candidate.md"


def _deny_result(paths: list[str], *, via_shell: bool) -> HookResult:
    rel_path = ", ".join(paths)
    via = " via shell" if via_shell else ""
    suggestion = _proposal_name_for(paths[0]) if paths else "<contract>.vN-candidate.md"
    reason = (
        f"converge/candidate-guard: BLOCKED direct write{via} to FROZEN file "
        f"'{rel_path}'.\n"
        "PROTOCOL.md §5 (pillar 3) / contracts/composition.v1.md clause 7: a "
        "locked contract changes by proposal, never by direct edit — by person "
        "or agent.\n"
        f"Remedy: write a sibling proposal '{suggestion}' "
        "(name shape '<contract>.vN-candidate.md'; the legacy "
        "'CANDIDATE-<topic>.md' is also admitted). A proposal has three parts, "
        "in order: (1) the exact change, sentence by sentence; (2) the evidence "
        "— a cost paid or a failure caught, since a preference is not evidence; "
        "(3) what does NOT change. The original stays the law until ratified: "
        "the OWNER ratifies with the literal word ('ratified' / 'ratified as "
        "edited' / declined-with-reason), and on ratification the edit lands "
        "via the escape hatch (see the module README / spec §2.7)."
    )
    user_message = (
        f"Blocked direct edit of locked {rel_path} — write {suggestion} instead "
        "(PROTOCOL.md §5, composition.v1 clause 7)."
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
        target = resolve_target_path(raw, cwd)
        if target is None:
            continue
        if _glob_match_any(target.rel, config.always_allow_globs):
            continue
        if not _glob_match_any(target.rel, config.guarded_globs):
            continue
        try:
            if _is_guarded(target.rel, config, target.root):
                guarded_hits.append(target.display)
        except Exception:  # noqa: BLE001 -- deliberate: fail-closed per spec §2.8
            if config.fail_closed_on_error:
                guarded_hits.append(target.display)
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

    guarded_paths: list[TargetPath] = []
    # converge-wu3y defect 1: content read once here, when the guarded-path
    # check itself reads it, is reused by the escape-hatch's already-landed
    # check below -- so that check never reads the same target a second
    # time (and so never has a second, independent chance to fail).
    guarded_content: dict[TargetPath, str | None] = {}
    unrecorded_locks: list[tuple[str, str]] = []
    for raw in raw_paths:
        target = resolve_target_path(raw, cwd)
        if target is None:
            # Step 9 (partial): outside cwd is out of this hook's scope (U9)
            continue

        # Step 5 -- always-allow (CANDIDATE) beats guarding, checked first
        if _glob_match_any(target.rel, config.always_allow_globs):
            continue

        # Step 6 -- guarded-path determination, with fail-closed on error
        if not _glob_match_any(target.rel, config.guarded_globs):
            continue
        try:
            guarded, content = _read_guarded_content(target.rel, config, target.root)
            # Step 6b -- the half-freeze check (converge-p17d). Only for a path
            # that is NOT already locked: a locked one is the deny path's, and
            # this check must never be what makes a locked file writable.
            if not guarded and config.require_lock_record:
                marker = _lock_without_record(
                    target.rel, tool_input, config, target.root
                )
                if marker is not None:
                    unrecorded_locks.append((target.display, marker))
        except Exception as exc:  # noqa: BLE001 -- deliberate: fail-closed per spec §2.8
            if config.fail_closed_on_error:
                return GuardDecision(
                    HookResult(
                        action="deny",
                        reason=(
                            f"converge/candidate-guard: guard evaluation error for "
                            f"'{target.display}': {exc}. Failing closed (spec §2.8)."
                        ),
                        user_message=(
                            f"Guard evaluation error for {target.display} — "
                            "failing closed."
                        ),
                        user_message_level="error",
                    )
                )
            continue
        if guarded:
            guarded_paths.append(target)
            guarded_content[target] = content

    if not guarded_paths:
        if unrecorded_locks:
            return GuardDecision(
                _lock_record_deny(unrecorded_locks),
                [
                    (
                        "converge:guard_blocked",
                        {
                            "path": rel,
                            "tool": tool_name,
                            "reason_code": "lock_without_record",
                        },
                    )
                    for rel, _ in unrecorded_locks
                ],
            )
        if config.enforce_encode_before_impl:
            gate_result = _check_encode_gate(raw_paths, config, cwd)
            if gate_result is not None:
                return GuardDecision(gate_result)
        return GuardDecision(HookResult(action="continue"))

    # Step 7/8 -- escape hatch per guarded path; deny if any lacks one
    events: list[tuple[str, dict[str, Any]]] = []
    blocked: list[str] = []
    for target in guarded_paths:
        try:
            escape = _check_escape_hatch(
                target.rel,
                config,
                target.root,
                target_content=guarded_content.get(target),
            )
        except Exception as exc:  # noqa: BLE001 -- deliberate: fail-closed per spec §2.8
            # converge-wu3y defect 1: an error evaluating the escape hatch
            # (e.g. a transient I/O failure re-reading the target when no
            # cached content was available) must never be read as "an
            # escape hatch was found" -- treat this guarded path as blocked
            # exactly as if _check_escape_hatch had returned None, and, per
            # the same fail-closed policy every other guard-evaluation
            # error uses, deny the whole call outright when
            # fail_closed_on_error is on (the default).
            if config.fail_closed_on_error:
                return GuardDecision(
                    HookResult(
                        action="deny",
                        reason=(
                            "converge/candidate-guard: guard evaluation error "
                            f"for '{target.display}': {exc}. Failing closed "
                            "(spec §2.8)."
                        ),
                        user_message=(
                            f"Guard evaluation error for {target.display} — "
                            "failing closed."
                        ),
                        user_message_level="error",
                    )
                )
            blocked.append(target.display)
            continue
        if escape is None:
            blocked.append(target.display)
        else:
            kind, detail = escape
            if kind == "ratified":
                events.append(
                    (
                        "converge:guard_allowed_ratified",
                        {"path": target.display, "candidate": detail},
                    )
                )
            else:
                events.append(
                    (
                        "converge:guard_unlock_used",
                        {"path": target.display, "token": detail},
                    )
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
