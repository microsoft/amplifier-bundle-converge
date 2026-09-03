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
  - bundle: sample-bad:behaviors/sample

# VIOLATES 1d: a session-wide spawn policy. This strips the named tools from
# EVERY spawned helper in EVERY session that composes this bundle, including
# work that has nothing to do with this project.
spawn:
  exclude_tools:
    - bash
    - delegate
    - load_skill
---

# Sample Bad

A fixture repository for the composition.v1 conformance kit.

## What this bundle provides

- **Recipe** — one, `@sample-bad:recipes/seed-reconcile.yaml`.

VIOLATES 1e: a second automated step file exists under `recipes/` that this
bundle declares nowhere. Its name is deliberately absent from this file.
