---
bundle:
  name: sample-bad
  version: 0.1.0
  description: >
    An intentionally non-conforming repository. It violates every checkable
    rule in the composition.v1 kit at once, so one run surfaces all of them
    instead of stopping at the first.

includes:
  # VIOLATES 1c: the heavy full-foundation package instead of the lean anchors
  # base. No anchors URI appears anywhere in these includes.
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundle.md
  # The shared work queue, on the ROOT path only. behaviors/sample.yaml does NOT
  # include it — see VIOLATES 5 in README.md.
  - bundle: git+https://github.com/microsoft/amplifier-work-tracker@main#subdirectory=behaviors/work-tracker.yaml
  - bundle: sample-bad:behaviors/sample

# VIOLATES 6a AND 6b: a session-wide spawn policy. This strips the named tools
# from EVERY spawned helper in EVERY session that composes this bundle,
# including work that has nothing to do with this project.
#
# The values are MODULE ids, not tool names, because that is what Amplifier's
# spawn policy filters on (`apply_spawn_tool_policy` matches `tool["module"]`).
# Written as `bash` / `delegate` / `load_skill` this block would look alarming
# and strip nothing — a fixture that cannot actually cause the harm it claims
# cannot serve as rule 6b's negative fixture, which installs this repository
# beside an unrelated session and measures what that session's helper loses.
spawn:
  exclude_tools:
    - tool-bash
    - tool-delegate
    - tool-skills
---

# Sample Bad

A fixture repository for the composition.v1 conformance kit.

## What this bundle provides

- **Recipe** — one, `@sample-bad:recipes/seed-reconcile.yaml`.

VIOLATES 1e: a second automated step file exists under `recipes/` that this
bundle declares nowhere. Its name is deliberately absent from this file.
