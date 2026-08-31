# hooks-candidate-guard

Structural enforcement of `PROTOCOL.md` §5 (pillar 3): **amendments are
CANDIDATE artifacts, never direct edits.** No direct write/edit/patch (or
bash write-laundering attempt) to a **FROZEN** contract file or `VISION.md`
is allowed; amendments go through a `CANDIDATE-<topic>.md` sibling and owner
ratification.

Full design: `docs/design/hooks-candidate-guard-spec.md`.

## What it does

Registers on `tool:pre` (priority 5) and, for each write-shaped tool call:

1. Extracts the target path(s) (`write_file`/`edit_file`: `file_path`;
   `apply_patch`: `path` + multi-file markers in `diff`/`patch`).
2. A path matching `always_allow_globs` (default `**/CANDIDATE-*.md`) is
   always allowed — this is the sanctioned amendment path.
3. A path is **guarded** iff it matches `guarded_globs` (default
   `contracts/*.md`, `contracts/**/*.md`, `docs/VISION.md`, `VISION.md`)
   **and** its *current* on-disk content carries the FROZEN/RATIFIED marker
   (`require_frozen_marker: true`, the default). A DRAFT contract being
   written during ENCODE is therefore **not** guarded yet.
4. A guarded path is denied **unless** a ratified `CANDIDATE-*.md` sibling
   names it as `target:` and carries the owner's ratified stamp (the escape
   hatch — see below), or (config-gated, off by default) an emergency-unlock
   token file names it.
5. `bash` commands are separately scanned for literal write-laundering
   patterns (redirection, `tee`, `sed -i`, `cp`/`mv` into, `truncate`,
   `dd of=`) naming a guarded path — denied on match.

Deny is fail-loud on both channels: `reason` (shown to the agent) names the
file, cites `PROTOCOL.md §5`, and states the remedy; `user_message`
(`level=error`) surfaces to the human.

## T2 confirmation — tool_name / field names (read live, not assumed)

The spec flagged this as the one thing to confirm before trusting the
shipped defaults. Confirmed by reading the actual composed tool sources
(not the kernel docs' Claude-Code-flavored examples):

- **`write_file`** — `amplifier_module_tool_filesystem/write.py`: `name =
  "write_file"`; `input_schema` requires `file_path` (+ `content`).
- **`edit_file`** — `amplifier_module_tool_filesystem/edit.py`: `name =
  "edit_file"`; `input_schema` requires `file_path` (+ `old_string`,
  `new_string`, `replace_all`).
- **`apply_patch`** — `amplifier_module_tool_apply_patch/tool.py`: `name =
  "apply_patch"`. The bundle's own default config
  (`amplifier-bundle-filesystem/behaviors/apply-patch.yaml`) sets
  `engine: native`, and `amplifier-foundation` includes exactly that
  behavior — so the tool_input shape actually composed by this bundle
  (via its `amplifier-foundation` include) is the **native** engine's:
  `{"type": "create_file"|"update_file"|"delete_file", "path": "<str>",
  "diff": "<str, optional>"}` — **one file per call**; the native engine
  explicitly *rejects* a `diff` containing V4A envelope markers
  (`*** Update File:` etc.), so multi-file marker parsing never actually
  fires against the composed default's `diff` field.
- **`bash`** — `amplifier_module_tool_bash/__init__.py`: `name = "bash"`;
  `input_schema` requires `command` (+ optional `timeout`, ...).

**Deviation from the spec's simplifying assumption:** §2.3 describes
`apply_patch` as if `path` + multi-file-marker-parsing-of-`diff` were a
single unified shape. In fact there are two distinct engine shapes for this
tool, and the multi-file V4A markers only ever appear in the **function**
engine's `patch` field (a full V4A envelope a target repo could opt into via
that tool's own `engine: function` config), never in the native engine's
`diff` field. `extract_paths()` is implemented to scan **both** `diff` and
`patch` for markers — harmless (no-op) against the composed default, and
correct if a repo switches `apply_patch` to the function engine. This is
the "robust to both" posture the spec explicitly asked for, extended one
step further once the real shapes were confirmed.

No live probe (spec Test Plan §5.2, T1–T6) was run as part of this
increment — those are DTU/live-session verifications, out of scope for a
static implementation pass. In particular **T5 (delegated-agent coverage)
is still open**: see "Known gaps" below.

## Known gaps (documented, not silently assumed away)

- **bash non-coverage.** Variable-constructed paths, `python -c`/`perl -e`
  writers, `base64 | sh`, and other obfuscation are **not** detected. The
  bundle's own sanctioned contract-writers use `write_file`/`edit_file`/
  `apply_patch`, never bash — the residual blast radius is a rogue agent
  hand-crafting an obfuscated bash write. Defense-in-depth backstop: a
  target-repo git `pre-commit` hook rejecting commits that modify a FROZEN
  file without a ratified CANDIDATE (out-of-bundle, not shipped here).
- **Delegated-agent coverage is unverified.** The kernel guarantees **no**
  automatic hook inheritance into forked sub-sessions
  (`SESSION_FORK_SPECIFICATION.md`, Kernel Guarantee #4: "Independence").
  Composing this hook at the bundle mount plan (as wired in `bundle.md`)
  covers the root session for certain. Whether a spawned agent (e.g.
  `foundation:file-ops`) also gets this hook is app-layer policy the kernel
  docs do not guarantee, and must be live-verified (spec Test Plan T5): spawn
  the agent, have it attempt a write to a frozen `contracts/*.md`, observe
  whether the guard denies. If it does not, the hook must additionally be
  composed into the EXECUTE-lane / delegated-agent overlays.
- **Rule (b), ENCODE-before-implement, is a coarse approximation.**
  `enforce_encode_before_impl` (off by default) denies an "implementation
  write" (not `.md`, not under a `tests/` path) while the phase marker
  `.converge/encoded` is absent. This only approximates "ENCODE committed";
  rule (a) — the CANDIDATE protocol — carries the real guarantee.

## Escape hatch — how a RATIFIED amendment lands

**Primary: ratified-CANDIDATE detection.** When a write targets a guarded
file, the handler looks for a sibling `CANDIDATE-*.md` (glob
`candidate_glob`) that (i) declares the guarded path via a `target:` line,
and (ii) carries the owner's ratified stamp matching `ratified_stamp_regex`
(default: a line starting `ratified` or `ratified as edited`, containing
`by owner`). If found, the write is allowed and
`converge:guard_allowed_ratified` is emitted.

**Fallback (break-glass, off by default): `emergency_unlock_token`.** A
git-tracked file (default path `.converge/UNLOCK`, only honored when
`allow_emergency_unlock: true`) with flat `file:` / `reason:` / `by:` lines
naming the one guarded path it unlocks. Committed → auditable; scoped to one
named file; never a global flag. Emits `converge:guard_unlock_used`.

**Single-landing hygiene:** after an amendment lands, the ratified
CANDIDATE is expected to be archived/removed in the same change (the frozen
file now carries the amended clause + a changelog entry). The guard does
not enforce single-use; this is a documented expectation, not a mechanism.

**Why not an env var:** an env var (`CONVERGE_RATIFIED=1`) is ambient —
un-scoped, un-audited, trivially left set. The ratified-CANDIDATE mechanism
is explicit (the owner must write the literal stamp), auditable (committed,
with a changelog entry), file-scoped (unlocks only the CANDIDATE's declared
`target`), and protocol-native (it *is* the §5 artifact, not a parallel
mechanism).

## Configuration

Every key below is overridable via the hook's `config:` block in
`bundle.md` — mechanism-not-policy (spec §2.5). See `bundle.md`'s
`hooks:` block for the full example with every default spelled out inline.

| Key | Default | Purpose |
|---|---|---|
| `enabled` | `true` | Master on/off switch. |
| `guarded_globs` | `["contracts/*.md", "contracts/**/*.md", "docs/VISION.md", "VISION.md"]` | Candidate files for guarding. |
| `require_frozen_marker` | `true` | Also require the FROZEN/RATIFIED marker in current content. |
| `frozen_marker_regex` | `(?im)^\*\*Status:\*\*\s*(?:RATIFIED|FROZEN)\|^status:\s*FROZEN` | How "frozen" is detected. |
| `always_allow_globs` | `["**/CANDIDATE-*.md"]` | Always allowed, checked before guarding. |
| `intercept_tools` | `["write_file", "edit_file", "apply_patch"]` | Native tool names to intercept. |
| `tool_name_aliases` | `["Write", "Edit", "MultiEdit"]` | Claude-Code-style aliases, same path handling as write_file/edit_file. |
| `path_fields` | `["file_path", "path"]` | Field name(s) to read the path from, in order. |
| `scan_bash` | `true` | Enable the bash write-laundering scan. |
| `bash_tool_name` | `"bash"` | Tool name treated as the shell. |
| `bash_write_patterns` | (six regexes) | Redirect/tee/dd/truncate/cp·mv/sed -i detection. |
| `escape_mode` | `"ratified_candidate"` | `ratified_candidate` \| `token` \| `both`. |
| `candidate_glob` | `["**/CANDIDATE-*.md"]` | Where to look for a ratified CANDIDATE. |
| `ratified_stamp_regex` | `(?im)^ratified(?:\s+as\s+edited)?\b.*\bby\s+owner\b` | The owner's literal ratification stamp. |
| `candidate_target_field` | `"target"` | Front-matter/line field naming the guarded path. |
| `allow_emergency_unlock` | `false` | Enable the break-glass token fallback. |
| `emergency_unlock_token` | `".converge/UNLOCK"` | Path to the token file (only read when enabled above). |
| `fail_closed_on_error` | `true` | Deny (don't continue) if evaluating a guarded-glob-matching path raises. |
| `enforce_encode_before_impl` | `false` | Opt-in rule (b), see "Known gaps". |
| `encode_marker_path` | `".converge/encoded"` | Phase marker rule (b) checks for. |

## Testing

`tests/test_guard.py` calls the pure functions in `guard.py` directly with
mock `tool:pre` data (`HOOK_CONTRACT.md` "Testing" pattern) — no live
session required. Run with:

```bash
uv run --with pytest --with pytest-asyncio pytest tests/
```
