# Implementation Spec — `hooks-candidate-guard` (converge increment 2)

**Status:** READY FOR BUILD. Complete enough for `modular-builder` to implement
without further design decisions. Every mechanism choice below is settled and,
where it depended on the kernel, cited to the authoritative contract.
**Owning design:** `docs/design/mechanism-spec.md` §6.1 (DECIDED: BUILD).
**Protocol source:** `@converge:docs/PROTOCOL.md` §5 (CANDIDATE protocol,
pillar 3), §4 Phase 2 (ENCODE-before-implement).
**Kernel contracts consulted:** `core:docs/contracts/HOOK_CONTRACT.md`,
`core:docs/HOOKS_API.md`, `core:docs/SESSION_FORK_SPECIFICATION.md`,
`core:docs/MODULE_SOURCE_PROTOCOL.md`.

> **Builder note — one thing to confirm live before trusting defaults.** The
> exact `tool_name` strings and `tool_input` field names as they arrive at
> `tool:pre` depend on which tool modules are composed. The kernel docs' own
> examples use Claude-Code names (`Write`/`Edit`, `tool_input.file_path`); this
> bundle composes the native `write_file`/`edit_file`/`apply_patch`. The design
> below is written to be **robust to both** (configurable name + field lists)
> and ships a live probe (Test Plan §T2) to confirm the real values — the same
> "verify, don't assume" discipline that caught increment 1's discovery≠
> composition defect. Treat the shipped defaults as a hypothesis the probe
> confirms.

---

## 1. Purpose

Structural enforcement of two PROTOCOL.md rules that convention alone cannot
hold (the behavioral model's OQ2/Scenario-E evidence: a per-tool policy cannot
distinguish an implementation write from any other write, nor a frozen-path edit
from any other path — mechanism-spec §2.2):

- **(a) CANDIDATE-not-direct-edit (PRIMARY, robustly enforceable).** No direct
  write to a **FROZEN** contract file or `VISION.md`. Amendments go through a
  `CANDIDATE-<topic>.md` sibling + owner ratification (PROTOCOL.md §5, pillar 3).
- **(b) ENCODE-before-implement (SECONDARY, opt-in / best-effort).** Block
  implementation writes before the ENCODE phase is committed (§4 Phase 2).
  Genuinely hard for a stateless hook to know "ENCODE committed" — scoped down
  to a checkable phase-marker mechanism and **off by default** (§4.6). Rule (a)
  is the load-bearing guarantee; rule (b) is a bonus the build may defer.

The enforcement is **path-aware (per-file)** — the capability per-tool policy
structurally lacks.

---

## 2. Mechanism — event, tools, deny (all cited)

### 2.1 Event registered

Register **one** handler on **`tool:pre`** — the pre-tool-execution event whose
data carries `tool_name` and `tool_input` (`HOOK_CONTRACT.md` "Common Events";
`HOOKS_API.md` "Hook Registration"). Registration in `mount()`:

```
coordinator.hooks.register("tool:pre", guard_handler, priority=5, name="candidate-guard")
```

Priority **5** (low = early; `HOOKS_API.md` "Parameters → priority") so the guard
evaluates before feedback/observation hooks.

### 2.2 Deny shape (cited)

Block with `HookResult(action="deny", reason=..., user_message=...,
user_message_level="error")`.

- `deny` is the **highest-precedence action; it short-circuits immediately and
  cannot be silently bypassed by any non-blocking handler** (`HOOKS_API.md`
  "Action Precedence"). This is exactly the "teeth" property the ratchet needs.
- `reason` is **shown to the agent** when blocked (`HOOKS_API.md` `reason`
  field); `user_message` (level `error`) surfaces to the human. Fail-loud in
  both channels — never silent.
- Handler signature is the contract protocol:
  `async def guard_handler(event: str, data: dict[str, Any]) -> HookResult`
  (`HOOK_CONTRACT.md` "Protocol Definition").

### 2.3 Tools intercepted + path extraction

Default `intercept_tools`: **`write_file`, `edit_file`, `apply_patch`** (native),
plus configurable aliases (`tool_name_aliases`, default `["Write","Edit",
"MultiEdit"]`) so a CC-named composition is still covered. Any `tool_name` not in
the union → `HookResult(action="continue")` immediately.

Path extraction (a helper `extract_paths(tool_name, tool_input) -> list[str]`):
- `write_file` / `edit_file`: read `tool_input["file_path"]` (fallback
  `tool_input["path"]`). Config `path_fields` default `["file_path","path"]`.
- `apply_patch`: read `tool_input["path"]` if present; **AND** parse the diff
  body (`tool_input.get("diff","")`) for file markers
  (`*** Update File: <p>` / `*** Add File: <p>` / `*** Delete File: <p>`, and
  `+++ b/<p>` unified-diff form) so a multi-file patch touching a guarded file is
  caught. Return every path found; the guard denies if **any** is guarded.
- Normalize each path to **repo-relative against the session cwd** (align with
  increment-1's within-cwd invariant, v1.2.0): `os.path.relpath(os.path.abspath(p),
  cwd)`. A path resolving **outside** cwd is treated as unguarded by this hook
  (out of scope) — it is the reconciler/recipe within-cwd invariant that keeps
  work inside the workspace.

### 2.4 `bash` — the laundering vector (settled: best-effort deny + documented non-coverage)

Full parse of an arbitrary shell command is impossible, so **do not pretend to
cover it completely.** Settled doctrine:

- **Scan** `bash` command strings (config `scan_bash: true`, `bash_tool_name:
  "bash"`) for the common write-laundering patterns that name a guarded path
  literally: output redirection (`>`, `>>`), `tee`, `sed -i`, `cp`/`mv` *into* a
  guarded path, `truncate`, `dd of=`. Config `bash_write_patterns` ships these as
  regexes. On a literal match against a guarded path → **`deny`** (not warn).
- **Justification for deny over warn:** a warn is silently bypassable, which
  defeats the ratchet; a bash write to a frozen contract is precisely the
  forbidden act. Deny-on-detected-match closes the cheap, common cases.
- **Documented non-coverage (honest gap, pillar 5):** variable-constructed
  paths, `python -c`/`perl -e` writers, `base64 | sh`, and other obfuscation are
  **not** detected and are declared out of coverage in the module README. The
  bundle's own sanctioned contract-writers use `write_file`/`edit_file` (fully
  covered), never bash — so the residual blast radius is "a rogue agent
  hand-crafting an obfuscated bash write," which is documented, not silently
  assumed away. Defense-in-depth for that residual is the target-repo git
  pre-commit backstop (§5.3), noted as out-of-bundle.

### 2.5 Guarded-path determination (mechanism-not-policy)

A path is **guarded** iff **both**:
1. it matches `guarded_globs` (default `["contracts/*.md","contracts/**/*.md",
   "docs/VISION.md","VISION.md"]`), **and**
2. `require_frozen_marker` is `true` (default) → the file's current content
   matches `frozen_marker_regex`
   (default `(?im)^\*\*Status:\*\*\s*(?:RATIFIED|FROZEN)|^status:\s*FROZEN`),
   i.e. it is actually FROZEN/RATIFIED. A **DRAFT** contract being written during
   ENCODE is therefore **not** guarded — the guard engages only once the file is
   stamped. (Set `require_frozen_marker: false` to guard by glob alone.)

**Always-allow override (the sanctioned path):** any write whose target matches
`always_allow_globs` (default `["**/CANDIDATE-*.md"]`) is allowed unconditionally
— `CANDIDATE-<topic>.md` is *how* you change a frozen clause. This check runs
**before** the guarded test so a CANDIDATE write can never be blocked.

The bundle ships the defaults; a target repo overrides any key via the hook's
`config:` block (mechanism-not-policy).

### 2.6 Block response — exact message shape

On a blocked write the handler returns:

```
HookResult(
  action="deny",
  reason=(
    "converge/candidate-guard: BLOCKED direct write to FROZEN file "
    f"'{rel_path}'.\n"
    "PROTOCOL.md §5 (pillar 3): amendments to a frozen vision/contract are "
    "CANDIDATE artifacts, never direct edits.\n"
    "Remedy: author a sibling 'CANDIDATE-<topic>.md' (exact diff · evidence · "
    "\"what does NOT change\" · ratification ask); the OWNER ratifies with the "
    "literal word ('ratified' / 'ratified as edited' / declined-with-reason). "
    "On ratification the edit lands via the escape hatch (see the module "
    "README / spec §2.7)."
  ),
  user_message=f"Blocked direct edit of frozen {rel_path} — use CANDIDATE-<topic>.md (PROTOCOL.md §5).",
  user_message_level="error",
)
```

Must name **the file**, **the rule (PROTOCOL.md §5)**, and **the remedy**. Never
silent.

### 2.7 Escape hatch — how a RATIFIED amendment lands (explicit, auditable, not ambient)

**PRIMARY: ratified-CANDIDATE detection.** When a write targets a guarded file,
the handler looks for a sibling `CANDIDATE-*.md` (config `candidate_glob`,
default `["**/CANDIDATE-*.md"]`) that (i) declares this file as its target — a
`target:` field/front-matter line naming the guarded path (the amendment-drafter
already emits the exact diff; add the `target:` line to its output), **and**
(ii) carries an owner ratification stamp matching `ratified_stamp_regex`
(default `(?im)^ratified(?:\s+as\s+edited)?\b.*\bby\s+owner\b`). If a matching,
ratified CANDIDATE exists → **allow** the write and emit
`converge:guard_allowed_ratified` (§6). Else → deny per §2.6.

- **Why this and not an env var:** an env var (`CONVERGE_RATIFIED=1`) is
  *ambient* — un-scoped, un-audited, trivially left set. Rejected by the task's
  "never ambient" constraint. The ratified-CANDIDATE is **explicit** (the owner
  must write the literal ratified stamp), **auditable** (the stamp is committed
  in the CANDIDATE, with a dated changelog entry per PROTOCOL.md §5),
  **file-scoped** (unlocks only the CANDIDATE's declared `target`), and
  **protocol-native** (it *is* the §5 artifact, not a parallel mechanism).
- **Single-landing hygiene:** after the amendment lands, the owner's ratified
  CANDIDATE is expected to be archived/removed in the same change (the frozen
  file now carries the amended clause + changelog entry). The guard does not
  need to enforce single-use, but the module README documents the expectation.

**FALLBACK (break-glass, config-gated, default off): `emergency_unlock_token`.**
A git-tracked token file (default path `.converge/UNLOCK`, only honored when
`allow_emergency_unlock: true`) whose YAML names `file:` (the exact guarded path
to unlock) + `reason:` + `by:`. Committed → auditable; scoped to one named file;
never a global flag. For amendments with no CANDIDATE (genuine emergencies). Emits
`converge:guard_unlock_used`.

### 2.8 Fail-closed on internal error (deliberate deviation, justified)

`HOOKS_API.md` "Error Handling" says hooks generally should not block on failure
— **except** "unless explicitly intended (e.g., validation failure should return
`deny` on purpose)." This hook is a validation gate, so: if evaluating a write
whose target **matches `guarded_globs`** raises (e.g., the frozen-marker read
fails), **fail closed** → `deny` with a "guard evaluation error" reason. If the
error occurs while evaluating a path that does **not** match `guarded_globs`,
`continue` (don't punish unrelated writes). Config `fail_closed_on_error: true`.

### 2.9 Delegated-agent coverage — SETTLED FROM CONTRACTS (the loophole that motivated this hook)

**Question:** do hooks composed in a parent session apply to spawned sub-sessions
(e.g. `foundation:file-ops`, EXECUTE-lane agents)?

**Answer — NO automatic inheritance is guaranteed by the kernel.** Evidence:
- `SESSION_FORK_SPECIFICATION.md`, **Kernel Guarantees #4: "Independence:
  Parent and child sessions are independent after fork."**
- Same doc, "Forked Session Lifecycle → Creation": a child session
  **`await child.initialize()` mounts modules per its OWN config**; and "What
  Kernel Does NOT Provide → Configuration Policy" — the kernel "does not …
  enforce inheritance rules." Child config is assembled by **app-layer merge**,
  not the kernel.
- `amplifier/docs/BUNDLES_PROVIDERS_ROUTING_PROJECTS.md` corroborates that
  session-only specializations "do not automatically pin delegated child
  sessions."

So a hook fires in a sub-session **only if it is in that sub-session's composed
mount plan.** Whether the app-cli's spawn/config-merge carries a bundle-level
`hooks:` block into each spawned agent's mount plan is **app-layer policy that
the kernel docs do not guarantee** — and is therefore an **empirical question**,
not a contract fact. (This is the exact class of gap that produced increment 1's
discovery≠composition defect, which lived in the app-cli `session_spawner`.)

**Mitigation (do not rely on inheritance):**
1. **Root coverage — guaranteed.** Composing the hook at the bundle mount plan
   (§3) covers the root session for certain.
2. **Live-verify propagation (Test Plan §T5)** before claiming sub-session
   coverage: spawn `foundation:file-ops`, have it attempt a write to a frozen
   `contracts/*.md`, observe whether the guard denies. Record the result the
   same way increment-1's probe was recorded.
3. **If propagation does NOT hold:** ensure the hook is present in the mount
   plans of the sessions that can write autonomously — i.e. compose it into the
   EXECUTE-lane / delegated-agent overlays (the app-layer surface that already
   carries per-agent config). The build must land whichever of {inherits
   automatically | must be added to agent overlays} the probe reveals — and the
   spec's acceptance is "a delegated write to a frozen file is denied, proven
   live," not "the hook is registered."
4. **Defense-in-depth backstop (out-of-bundle, documented):** a target-repo git
   `pre-commit` hook rejecting commits that modify a FROZEN file without a
   ratified CANDIDATE. Catches anything that slips every in-session guard
   (including the bash obfuscation residual of §2.4). Noted as target-repo
   policy, not shipped by this bundle.

**This is the honest gap for the owner to note:** #2/#3 cannot be closed from
the contracts alone — the kernel guarantees independence, so sub-session coverage
is a live-verified property, not an assumed one.

---

## 3. Bundle wiring

### 3.1 The `hooks:` block for `bundle.md`

Same-repo module source convention (confirmed against
`amplifier-bundle-attractor/behaviors/attractor-core.yaml`, which wires its own
`modules/hooks-*` this way, and increment-1's work-tracker include): the bundle
references its **own** module by the published git URL + `#subdirectory=`.

```yaml
hooks:
  - module: hooks-candidate-guard
    source: git+https://github.com/microsoft/amplifier-bundle-converge@main#subdirectory=modules/hooks-candidate-guard
    config:
      enabled: true
      guarded_globs: ["contracts/*.md", "contracts/**/*.md", "docs/VISION.md", "VISION.md"]
      require_frozen_marker: true
      frozen_marker_regex: '(?im)^\*\*Status:\*\*\s*(?:RATIFIED|FROZEN)|^status:\s*FROZEN'
      always_allow_globs: ["**/CANDIDATE-*.md"]
      intercept_tools: ["write_file", "edit_file", "apply_patch"]
      tool_name_aliases: ["Write", "Edit", "MultiEdit"]
      path_fields: ["file_path", "path"]
      scan_bash: true
      bash_tool_name: "bash"
      escape_mode: "ratified_candidate"        # ratified_candidate | token | both
      candidate_glob: ["**/CANDIDATE-*.md"]
      ratified_stamp_regex: '(?im)^ratified(?:\s+as\s+edited)?\b.*\bby\s+owner\b'
      candidate_target_field: "target"
      allow_emergency_unlock: false
      emergency_unlock_token: ".converge/UNLOCK"
      fail_closed_on_error: true
      enforce_encode_before_impl: false        # rule (b), opt-in — see §4.6
```

> **Pre-publication note:** `amplifier-bundle-converge` is not published yet.
> `MODULE_SOURCE_PROTOCOL.md` documents a `FileSource` (local filesystem) source
> type alongside `GitSource`; during local dev/DTU the build MAY use a local
> path source for `modules/hooks-candidate-guard`, switching to the
> `git+…#subdirectory=` form on publish. Do not hardcode an absolute path in the
> committed bundle.

### 3.2 On by default? — YES (stated position)

**Position: yes, on by default when the bundle is composed.** It is the ratchet's
teeth — the structural half of "amendments are CANDIDATE artifacts." A guard that
ships off-by-default recreates exactly the convention-only gap the behavioral
model proved insufficient (OQ2). `enabled: true` is the default; a repo can set
`enabled: false` to opt out explicitly and auditably (config, not ambient).

### 3.3 Module layout (matches attractor convention)

```
modules/hooks-candidate-guard/
  pyproject.toml                 # entry point below
  amplifier_module_hooks_candidate_guard/
    __init__.py                  # async def mount(coordinator, config) -> cleanup
    guard.py                     # handler + pure helpers (path match, extract, bash scan, escape)
  tests/
    test_guard.py
  README.md                      # documents bash non-coverage + escape hatch + delegated-agent status
```

`pyproject.toml` entry point (`HOOK_CONTRACT.md` "pyproject.toml"):
```toml
[project.entry-points."amplifier.modules"]
hooks-candidate-guard = "amplifier_module_hooks_candidate_guard:mount"
```

`mount()` returns a cleanup callable that unregisters the handler
(`HOOK_CONTRACT.md` "Entry Point Pattern"). Register observability events via
`coordinator.register_contributor("observability.events", "hooks-candidate-guard",
lambda: ["converge:guard_blocked", "converge:guard_allowed_ratified",
"converge:guard_unlock_used"])` (§6).

---

## 4. Handler logic (decision order — implement exactly)

For each `tool:pre` event:

1. If `not config.enabled` → `continue`.
2. If `tool_name` is `bash_tool_name` and `scan_bash` → run §2.4 bash scan;
   on a guarded-path match → `deny` (§2.6 message, "via shell"); else `continue`.
3. If `tool_name` ∉ (`intercept_tools` ∪ `tool_name_aliases`) → `continue`.
4. `paths = extract_paths(...)` (§2.3), normalized repo-relative.
5. For each path: if it matches `always_allow_globs` → `continue` (CANDIDATE is
   sanctioned — checked before guarding).
6. Determine guarded set (§2.5). If none guarded → `continue`.
7. For each guarded path: if the escape hatch (§2.7) validates for that path →
   allow + emit `converge:guard_allowed_ratified` (or `_unlock_used`).
8. Otherwise → `deny` (§2.6), emit `converge:guard_blocked`.
9. Any exception inside 4–8 for a `guarded_globs`-matching path → fail closed
   (`deny`) per §2.8; otherwise `continue`.

### 4.6 Rule (b) ENCODE-before-implement (opt-in, `enforce_encode_before_impl`)

Off by default. When on: an **implementation write** (a write to a path *not*
matching `guarded_globs` and *not* a doc/test) is denied while a phase marker
`.converge/encoded` is **absent** (the `encode` recipe's `commit-encoded` step
writes this marker on commit). Honest limit: this only approximates "ENCODE
committed"; it is a coarse phase gate, which is why it is opt-in and why rule (a)
carries the real guarantee. Builder may defer 4.6 to a later increment without
weakening rule (a).

---

## 5. Test plan

### 5.1 Unit tests (`tests/test_guard.py`, pure — no live session)

Call the handler directly with mock `tool:pre` data (per `HOOK_CONTRACT.md`
"Testing" pattern). Assert on `HookResult.action`/`reason`.

- **U1 path match:** write to `contracts/automation-file.v1.md` (content stamped
  FROZEN) → `deny`; write to `src/foo.py` → `continue`.
- **U2 frozen-marker gating:** write to a `contracts/draft.md` **without** the
  frozen marker, `require_frozen_marker: true` → `continue` (DRAFT writable);
  same file once it contains the FROZEN stamp → `deny`.
- **U3 CANDIDATE allowance:** write to `contracts/CANDIDATE-retry-policy.md` →
  `continue` (always-allow beats guard).
- **U4 block message shape:** on a blocked write assert `reason` contains the
  file path, `"PROTOCOL.md §5"`, and `"CANDIDATE-"`; `user_message_level ==
  "error"`.
- **U5 escape hatch (ratified CANDIDATE):** guarded write with a sibling
  `CANDIDATE-*.md` whose `target:` names the file and body matches
  `ratified_stamp_regex` → `continue`; same without the stamp → `deny`; stamp
  present but `target:` names a *different* file → `deny` (scope is per-file).
- **U6 apply_patch multi-file:** `apply_patch` whose diff body touches
  `contracts/x.v1.md` (frozen) among other files → `deny`.
- **U7 bash scan:** `bash` `echo x >> contracts/x.v1.md` → `deny`;
  `bash` `pytest -q` → `continue`; documented-non-coverage case
  (`bash` `python -c "open('contracts/x.v1.md','w')..."`) → `continue`
  **and** asserted as a known gap (test documents, does not fail).
- **U8 fail-closed:** monkeypatch the frozen-marker read to raise for a
  `guarded_globs` path → `deny`; raise for a non-guarded path → `continue`.
- **U9 within-cwd:** an absolute path resolving outside cwd → `continue` (out of
  this hook's scope; within-cwd invariant owns that boundary).
- **U10 mount/cleanup:** `mount(TestCoordinator(), config)` registers on
  `tool:pre`; returned cleanup unregisters (per `HOOK_CONTRACT.md` "Testing").

### 5.2 Live-verification probes (run in the DTU after build — the D5/loophole closers)

- **T1 root write blocked:** root session attempts `write_file` to a frozen
  `contracts/*.md` → denied with the §2.6 message.
- **T2 tool_name/field confirmation:** capture a real `tool:pre` payload for
  `write_file`/`edit_file`/`apply_patch` in the composed session; confirm the
  actual `tool_name` strings and path field names; reconcile against the shipped
  `intercept_tools`/`path_fields` defaults (adjust config if the probe disagrees).
- **T3 CANDIDATE allowed:** writing `CANDIDATE-<topic>.md` proceeds.
- **T4 escape hatch lands:** with a ratified CANDIDATE present, the amendment
  write to the frozen file proceeds; `converge:guard_allowed_ratified` emitted.
- **T5 delegated-agent coverage (the loophole):** spawn `foundation:file-ops`
  and have it attempt a write to a frozen `contracts/*.md`. **Record** whether
  the guard denies. If NO → apply §2.9 mitigation #3 (compose the hook into the
  agent overlay) and re-probe until a delegated write to a frozen file is denied.
- **T6 bash redirection blocked:** a lane using `bash` `>>` into a frozen file is
  denied.

Acceptance = T1, T3, T4, T6 green **and** T5 green (delegated write denied,
however coverage was achieved) **and** T2 reconciled.

### 5.3 Live-verification RESULTS (2026-08-30, host probes against a disposable fixture repo)

All probes run with the converge bundle composed from the local checkout
(`amplifier run --bundle converge`) in a scratch repo with a FROZEN
`contracts/probe.v1.md` and a DRAFT `contracts/draft.v1.md`:

- **T1 GREEN** — root `write_file` to the FROZEN contract denied:
  "Denied by hook: converge/candidate-guard: BLOCKED direct write to FROZEN
  file 'contracts/probe.v1.md'."
- **T2 RECONCILED statically** — tool_name strings and field names confirmed
  from composed tool sources (write_file/edit_file `file_path`, apply_patch
  native `path`+`diff` vs function-engine `patch`, bash `command`); shipped
  defaults match.
- **T3 GREEN** — `CANDIDATE-*.md` creation allowed AND DRAFT-contract edit
  allowed (FROZEN-marker gating works both directions).
- **T4 GREEN (escape hatch)** — with a ratified CANDIDATE present
  (`target:` + "Ratified as edited — … by owner"), the amendment write to the
  FROZEN file proceeded; ground truth verified in file bytes.
- **T5 GREEN — the loophole is CLOSED with live evidence:** a delegated
  `foundation:file-ops` sub-agent's write to the FROZEN contract was DENIED
  by the guard, and ground truth confirmed the file untouched. Hook
  propagation to spawned sub-sessions holds in this app's composition
  (app-layer merge policy, per §2.9 — property remains live-verified, not
  kernel-guaranteed; re-probe if the spawner changes).
- **T6 GREEN** — bash `>>` redirect into the FROZEN file denied, message
  cited PROTOCOL.md §5 and the CANDIDATE remedy.

**Acceptance met.** No §2.9 mitigation needed at this time.

---

## 6. Observability

Emit (and register via contribution channel, `HOOK_CONTRACT.md` "Observability"):
`converge:guard_blocked` (path, tool, reason-code), `converge:guard_allowed_ratified`
(path, candidate), `converge:guard_unlock_used` (path, token). These give the
audit trail that "every frozen-file change went through ratification."

---

## 7. Settled decisions (index)

| # | Decision point | Settled answer |
|---|---|---|
| 1 | Event | `tool:pre`, handler `async (event,data)->HookResult`, priority 5 (HOOK_CONTRACT) |
| 2 | Deny | `HookResult(action="deny", reason=…, user_message=…, level=error)` — highest precedence, non-bypassable (HOOKS_API) |
| 3 | Tools | `write_file`/`edit_file`/`apply_patch` + configurable CC aliases; confirm live (T2) |
| 4 | bash | best-effort literal-path scan → **deny** on match; obfuscation documented non-coverage |
| 5 | Guarded-path | `guarded_globs` AND FROZEN-marker; `CANDIDATE-*.md` always allowed; repo-overridable |
| 6 | Block message | names file + PROTOCOL.md §5 + CANDIDATE remedy; fail-loud both channels |
| 7 | Escape hatch | ratified-CANDIDATE (explicit/auditable/file-scoped/protocol-native); token break-glass fallback; env var rejected |
| 8 | Error | fail-closed (deny) for guarded paths; continue otherwise |
| 9 | Delegated coverage | kernel guarantees NO inheritance (SESSION_FORK §Guarantees #4); live-verify + compose-into-overlays; git backstop |
| 10 | Wiring | own-repo `git+…#subdirectory=modules/hooks-candidate-guard`; on by default |
