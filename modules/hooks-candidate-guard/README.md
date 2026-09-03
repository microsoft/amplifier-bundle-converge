# hooks-candidate-guard

Structural enforcement of `contracts/composition.v1.md` clause 7 and
`PROTOCOL.md` §5 (pillar 3): **a locked contract changes by proposal, never by
direct edit — by person or agent.** No direct write/edit/patch (or bash
write-laundering attempt) to a **locked** (FROZEN) contract file or `VISION.md`
is allowed; changes go through a sibling proposal file and owner ratification.

Full design: `docs/design/hooks-candidate-guard-spec.md`.

## Changelog

### 2026-09-02 — the guard now reads the ratified anatomy, on both write paths

**Root cause, one sentence: the guard's notion of "a locked contract" and "a
proposal file" lagged the ratified anatomy, and one write path never reached
the guard at all.** Four reports were filed independently and collapse into
two fixes. Three of them — `converge-diw` (the guard read
`**Status:** FROZEN`, while `contracts/documents.v1.md` clause 6 mandates that
status lives in the H1 parenthetical `(FROZEN <date>)` *and nowhere else*, the
form `.githooks/pre-push` already checked), `converge-9vw` and `converge-ksg`
(the guard admitted only the legacy `CANDIDATE-*.md`, while clause 8 mandates
`<contract>.vN-candidate.md` — so a proposal under the mandated name was
neither writable beside a locked contract nor findable by the escape hatch,
and a contract locked per the contracts was not guarded at all) — are all the
same drift: **the documents were ratified forward and the guard was left
behind, in two places at once (the module defaults and the shipped
`behaviors/converge.yaml`), which is why fixing one never fixed the symptom.**
They are fixed together by teaching `frozen_marker_regex` the H1 form
alongside the legacy body markers, and by a test that asserts the module
defaults and the shipped config cannot silently diverge again. The fourth,
`converge-ldz` (`amplifier tool invoke` wrote a locked contract unimpeded),
has a different cause and gets its own fix — see "The two write paths" below.

Not a wording change to any contract: the contracts were already right. The
guard moved to them.

## The two proposal names

The guard admits **both** sanctioned proposal filenames beside a locked
contract, and refuses every other write to that contract:

| Name | Where it comes from | Status |
|---|---|---|
| `<contract>.vN-candidate.md` | `contracts/documents.v1.md` clause 8 | Preferred |
| `CANDIDATE-<topic>.md` | `PROTOCOL.md` §5 | Legacy, still admitted |

For a locked `contracts/composition.v1.md`, the preferred proposal is
`contracts/composition.v2-candidate.md` — the guard's deny message computes
and names that exact path, so the reader is never left to decode a template.

Both are matched by `PROPOSAL_GLOBS` in `guard.py`
(`**/*.v[0-9]*-candidate.md`, `**/CANDIDATE-*.md`), which is the default for
both `always_allow_globs` (what may be written) and `candidate_glob` (where a
ratified proposal is looked for). The `vN` segment requires a real digit:
`x.v2-candidate.md` is a proposal, `x.vN-candidate.md` and `x.candidate.md`
are not.

### What a proposal contains

Three parts, in order (`contracts/documents.v1.md` clause 8):

1. **The exact change**, sentence by sentence.
2. **The evidence** — a cost paid or a failure caught. *A preference is not
   evidence.*
3. **What does NOT change.**

The original stays the law until ratified. The guard checks the *name*, not
these three parts; the shape is enforced by the conformance kit and by review,
not by this hook.

A proposal must also carry a `target:` line naming the locked file it amends —
under **both** names. The guard never infers which contract a proposal amends
from its filename alone, so `x.v2-candidate.md` does not implicitly unlock
`x.v1.md` until it says so and the owner ratifies it.

## What "locked" means

A guarded file is locked when its current on-disk content carries any of three
markers (`frozen_marker_regex`, `require_frozen_marker: true`):

| Marker | Where it comes from | Status |
|---|---|---|
| `(FROZEN <date>)` in the H1 | `contracts/documents.v1.md` clause 6 | **The ratified form** — status lives here and nowhere else. Also what `.githooks/pre-push` checks. |
| `**Status:** FROZEN` / `**Status:** RATIFIED` | earlier convention | Legacy, still detected |
| `status: FROZEN` | earlier convention | Legacy, still detected |

`(DRAFT)` in the H1 is **not** a lock — a contract being authored during
ENCODE stays writable.

The H1 branch is deliberately loose (any `#`-led line, case-insensitive):
over-matching only ever guards *more*, whereas a guard that under-matches
fails silently — which is exactly how a contract locked per the contracts went
unguarded. Proposal files that quote a locked H1 are unaffected, because
`always_allow_globs` is checked before guarding.

The module's default and the shipped `behaviors/converge.yaml` value are
**byte-identical on purpose**, and a test asserts it: they disagreed once, and
that disagreement is half of why four reports were filed.

## The two write paths

The guard covers both ways a write can reach the filesystem in a session.

| Path | Who takes it | How the guard sees it |
|---|---|---|
| `tool:pre` | the orchestrator, for every tool call an agent makes | a registered hook handler (priority 5) |
| `tools[name].execute(...)` | `amplifier tool invoke`, and anything else that dispatches a tool directly | the guard wraps each mounted tool instance's own `execute` |

**Why the second path exists (`converge-ldz`).** Measured 2026-09-02, not
inferred: in the session `amplifier tool invoke` builds, this hook *is*
mounted and *is* registered on `tool:pre` — and the write landed anyway.
`amplifier_app_cli/commands/tool.py::_invoke_tool_from_bundle_async` builds a
full session and then calls `tool_instance.execute(tool_args)` itself. No
`tool:pre` is ever emitted, so **no hook registered on that event — not this
one, not any — can intercept it.** That is an app-layer dispatch property, not
something a hook can fix from the `tool:pre` side.

What makes the wrap possible is mount order:
`amplifier_core/_session_init.py` mounts, in sequence, orchestrator → context
→ providers → **tools** → **hooks**. Every tool instance therefore already
exists in the coordinator when this hook mounts. Wrapping is per **instance**,
never on the class, so it cannot leak into an unrelated session that merely
imports the same tool module; `mount()`'s cleanup restores each original.

A denied direct-dispatch write **raises** `CandidateGuardBlocked` rather than
returning an error dict — a returned dict is indistinguishable from success to
a caller that does not inspect it, while `amplifier tool invoke` prints a
raised exception and exits non-zero. Off switch: `wrap_tool_execute: false`.

A tool mounted *after* the hooks phase (by an `on_session_ready` callback) is
not wrapped; the `tool:pre` path still guards it. If a tool cannot be wrapped
at all (slotted / read-only instance), the module logs a warning naming that
tool rather than degrading silently.

## What it does

Registers on `tool:pre` (priority 5) and, for each write-shaped tool call:

1. Extracts the target path(s) (`write_file`/`edit_file`: `file_path`;
   `apply_patch`: `path` + multi-file markers in `diff`/`patch`).
2. A path matching `always_allow_globs` (default: both proposal names above)
   is always allowed — this is the sanctioned amendment path. It is checked
   **first**, before guarding, because a proposal's first part quotes the
   locked contract's own text (status line included), so a proposal file will
   often read as frozen itself.
3. A path is **guarded** iff it matches `guarded_globs` (default
   `contracts/*.md`, `contracts/**/*.md`, `docs/VISION.md`, `VISION.md`)
   **and** its *current* on-disk content carries the FROZEN/RATIFIED marker
   (`require_frozen_marker: true`, the default). A DRAFT contract being
   written during ENCODE is therefore **not** guarded yet.
4. A guarded path is denied **unless** a ratified proposal sibling (either
   name) declares it as `target:` and carries the owner's ratified stamp (the
   escape hatch — see below), or (config-gated, off by default) an
   emergency-unlock token file names it.
5. `bash` commands are separately scanned for literal write-laundering
   patterns (redirection, `tee`, `sed -i`, `cp`/`mv` into, `truncate`,
   `dd of=`) naming a guarded path — denied on match.

Deny is fail-loud on both channels: `reason` (shown to the agent) names the
file, cites `PROTOCOL.md §5` and `composition.v1` clause 7, names the exact
proposal filename to write instead, and spells out the three-part shape;
`user_message` (`level=error`) surfaces to the human with the same remedy.

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

The live probes T1–T6 (spec Test Plan §5.2) were run on 2026-08-30 against a
disposable fixture repo and all recorded GREEN — results in spec §5.3,
including T5 (delegated-agent coverage), which closed the propagation
loophole with live evidence.

**T1-T6 remain green across the 2026-09-02 change, by construction rather than
by re-running.** The hook-registration call is byte-identical, the interception
surface (`intercept_tools`, `tool_name_aliases`, `path_fields`,
`bash_write_patterns`, `guarded_globs`) is untouched, and the single
behavioural change -- an added alternation branch in `frozen_marker_regex`,
consumed as `bool(re.search(...))` -- is **monotonic**: every string that
matched before still matches, so `_is_guarded` now returns True on a strict
superset. A probe asserting "the write was denied" cannot flip red under a
strictly-more-denying predicate.

**A NEW question the probes never covered:** does the `execute` wrapper
propagate into a spawned sub-session? That is not T5 -- T5 exercises the
`tool:pre` path, which is unchanged. The wrapper is a second mechanism, and a
sub-session has its own coordinator and its own tool instances, so it is
protected only if the guard is composed there and mounts after that session's
tools. Expected to hold by the same tools-before-hooks ordering, but the
kernel guarantees no automatic hook inheritance, so treat delegated-agent
coverage of the *direct-dispatch* path as **unverified** until probed.

The two-proposal-name change did **not** touch the interception surface those
probes exercise: `intercept_tools`, `tool_name_aliases`, `path_fields`,
`bash_write_patterns`, and the mount wiring are all unchanged, so T2 (tool
name/field reconciliation) and T5 (propagation into spawned sub-sessions)
are unaffected by it. T1 (locked write denied), T3 (proposal allowed, DRAFT
allowed), T4 (ratified proposal lands the amendment) and T6 (bash redirect
denied) are each mirrored by a unit test in the `W1` block of
`tests/test_guard.py`, run against **both** proposal names.

## Known gaps (documented, not silently assumed away)

- **bash non-coverage.** Variable-constructed paths, `python -c`/`perl -e`
  writers, `base64 | sh`, and other obfuscation are **not** detected. The
  bundle's own sanctioned contract-writers use `write_file`/`edit_file`/
  `apply_patch`, never bash — the residual blast radius is a rogue agent
  hand-crafting an obfuscated bash write. Defense-in-depth backstop: a
  target-repo git `pre-commit` hook rejecting commits that modify a FROZEN
  file without a ratified CANDIDATE (out-of-bundle, not shipped here).
- **Direct tool dispatch is covered, but by a wrapper, not by the hook.** See
  "The two write paths". `amplifier tool invoke` emits no `tool:pre` at all,
  so the coverage comes from wrapping each mounted tool instance's `execute`.
  Two honest limits follow: a tool mounted *after* the hooks phase (via an
  `on_session_ready` callback) is not wrapped, and a caller that reaches into
  a tool's *internals* rather than calling `execute` is not seen either. Both
  degrade to `tool:pre`-only coverage, and neither is silent — the module
  warns when it cannot wrap.
- **Delegated-agent coverage is live-verified, not kernel-guaranteed.** The
  kernel guarantees **no** automatic hook inheritance into forked sub-sessions
  (`SESSION_FORK_SPECIFICATION.md`, Kernel Guarantee #4: "Independence").
  Composing this hook at the bundle mount plan covers the root session for
  certain. Whether a spawned agent also gets it is app-layer policy the kernel
  docs do not guarantee. Probe T5 (spec §5.3) found it **does** hold in this
  app's composition — a delegated `foundation:file-ops` write to a FROZEN
  contract was denied — but that is a live-verified property, not a promise:
  **re-probe whenever the spawner or the composition changes.**
- **Rule (b), ENCODE-before-implement, is a coarse approximation.**
  `enforce_encode_before_impl` (off by default) denies an "implementation
  write" (not `.md`, not under a `tests/` path) while the phase marker
  `.converge/encoded` is absent. This only approximates "ENCODE committed";
  rule (a) — the CANDIDATE protocol — carries the real guarantee.

## Escape hatch — how a RATIFIED amendment lands

**Primary: ratified-proposal detection.** When a write targets a guarded
file, the handler looks for a sibling proposal under **either** name —
`<contract>.vN-candidate.md` or `CANDIDATE-*.md` (glob `candidate_glob`) —
that (i) declares the guarded path via a `target:` line, and (ii) carries the
owner's ratified stamp matching `ratified_stamp_regex` (default: a line
starting `ratified` or `ratified as edited`, containing `by owner`). If found,
the write is allowed and `converge:guard_allowed_ratified` is emitted. Both
names use the identical mechanism — admitting the new name for *writing* a
proposal while the escape hatch still recognised only the old one would leave
a ratified proposal unable to land.

**Fallback (break-glass, off by default): `emergency_unlock_token`.** A
git-tracked file (default path `.converge/UNLOCK`, only honored when
`allow_emergency_unlock: true`) with flat `file:` / `reason:` / `by:` lines
naming the one guarded path it unlocks. Committed → auditable; scoped to one
named file; never a global flag. Emits `converge:guard_unlock_used`.

**Single-landing hygiene:** after an amendment lands, the ratified
proposal is expected to be archived/removed in the same change (the locked
file now carries the amended clause + a changelog entry). The guard does
not enforce single-use; this is a documented expectation, not a mechanism.

**Why not an env var:** an env var (`CONVERGE_RATIFIED=1`) is ambient —
un-scoped, un-audited, trivially left set. The ratified-proposal mechanism
is explicit (the owner must write the literal stamp), auditable (committed,
with a changelog entry), file-scoped (unlocks only the proposal's declared
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
| `frozen_marker_regex` | `(?im)^\*\*Status:\*\*\s*(?:RATIFIED|FROZEN)\|^status:\s*FROZEN\|^#.*\(FROZEN\b` | How "locked" is detected — the ratified H1 form plus both legacy body markers. Byte-identical to the shipped `behaviors/converge.yaml` value; a test asserts they cannot diverge. |
| `always_allow_globs` | `["**/*.v[0-9]*-candidate.md", "**/CANDIDATE-*.md"]` | Both proposal names — always allowed, checked before guarding. |
| `intercept_tools` | `["write_file", "edit_file", "apply_patch"]` | Native tool names to intercept. |
| `tool_name_aliases` | `["Write", "Edit", "MultiEdit"]` | Claude-Code-style aliases, same path handling as write_file/edit_file. |
| `path_fields` | `["file_path", "path"]` | Field name(s) to read the path from, in order. |
| `scan_bash` | `true` | Enable the bash write-laundering scan. |
| `bash_tool_name` | `"bash"` | Tool name treated as the shell. |
| `bash_write_patterns` | (six regexes) | Redirect/tee/dd/truncate/cp·mv/sed -i detection. |
| `escape_mode` | `"ratified_candidate"` | `ratified_candidate` \| `token` \| `both`. |
| `candidate_glob` | `["**/*.v[0-9]*-candidate.md", "**/CANDIDATE-*.md"]` | Where to look for a ratified proposal (both names). |
| `ratified_stamp_regex` | `(?im)^ratified(?:\s+as\s+edited)?\b.*\bby\s+owner\b` | The owner's literal ratification stamp. |
| `candidate_target_field` | `"target"` | Front-matter/line field naming the guarded path. Required under both proposal names. |
| `allow_emergency_unlock` | `false` | Enable the break-glass token fallback. |
| `emergency_unlock_token` | `".converge/UNLOCK"` | Path to the token file (only read when enabled above). |
| `fail_closed_on_error` | `true` | Deny (don't continue) if evaluating a guarded-glob-matching path raises. |
| `wrap_tool_execute` | `true` | Also guard direct tool dispatch by wrapping each mounted tool's `execute` — the `amplifier tool invoke` path, which emits no `tool:pre`. |
| `enforce_encode_before_impl` | `false` | Opt-in rule (b), see "Known gaps". |
| `encode_marker_path` | `".converge/encoded"` | Phase marker rule (b) checks for. |

## Testing

`tests/test_guard.py` calls the pure functions in `guard.py` directly with
mock `tool:pre` data (`HOOK_CONTRACT.md` "Testing" pattern) — no live
session required. Run with:

```bash
uv run --with pytest --with pytest-asyncio pytest tests/
```

Three blocks: `U1`–`U10` follow spec §5.1; `W1` covers `composition.v1`
clause 7 (both proposal names); `W3` covers the ratified H1 locked marker and
the second write path (`converge-diw` / `-9vw` / `-ksg` / `-ldz`).

The W1 and W3 proposal cases seed the proposal file as **already existing and
already carrying a locked marker** — that is the case that actually
discriminates. Writing to a path that does not exist yet proves nothing: a
missing file can never read as locked, so it is admitted with or without the
allowance.

`W3` also carries two tests that exist to catch a silent regression rather
than a behaviour:

- `test_w3a_module_default_matches_the_shipped_behavior_config` reads
  `behaviors/converge.yaml` and asserts the module defaults and the shipped
  config agree on `frozen_marker_regex`, `always_allow_globs` and
  `candidate_glob`. Their disagreement is half the cause of the four reports.
- `test_w3d_wrapping_is_opt_outable_and_idempotent` is the removal control for
  the `execute` wrapper: with `wrap_tool_execute: false` nothing is touched,
  so the pre-fix behaviour is exactly recoverable.

### Live evidence (2026-09-02)

The wrapper was verified against the real composed session, not only in
unit tests. Fixture: a scratch repo with `contracts/probe.v1.md` whose H1 is
`# Probe Contract — v1 (FROZEN 2026-09-02)` and which carries no `**Status:**`
line at all.

| Probe | Expected | Result |
|---|---|---|
| `write_file` on the H1-locked contract | deny | `CandidateGuardBlocked`, file unchanged (128 bytes) |
| same, before the fix | *(the defect)* | wrote it — 128 → 8 bytes |
| `contracts/probe.v2-candidate.md` beside it | allow | written |
| `contracts/CANDIDATE-probe.md` beside it | allow | written |
| `(DRAFT)` contract | allow | written |
| legacy `**Status:** FROZEN`, no H1 status | deny | blocked, file unchanged |
| `bash` redirect into the locked contract | deny | blocked, file unchanged |
| ordinary unguarded file | allow | written |
| ratified `probe.v2-candidate.md` → edit the locked contract | allow | landed |
| same proposal *unratified* | deny | blocked |

**One deviation, stated rather than buried:** the probe reproduces
`_invoke_tool_from_bundle_async` verbatim but excludes **app bundles** from
composition. Two converge behaviors are registered as app bundles from git on
that host, and their copy of this module shadows the worktree copy under test
(composition dedupes to one). Re-probing this from a lane needs its own stable
bundle registration *and* that exclusion, or it silently measures a different
module — which is what makes this failure mode worth writing down.
