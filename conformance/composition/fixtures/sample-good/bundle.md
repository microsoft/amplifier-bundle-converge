---
bundle:
  name: sample-good
  version: 0.1.0
  description: >
    A minimal repository that conforms to composition.v1. It assembles on the
    lean base, its one automated step uses only lean-base helpers, it declares
    no session-wide spawn policy, and its guard admits a proposal beside a
    locked contract under either name.

includes:
  # The LEAN BASE (composition.v1 Core 1).
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main#subdirectory=bundles/anchors/bundle.md
  - bundle: sample-good:behaviors/sample

# NO top-level `spawn:` block — deliberately (composition.v1 Core 6). A
# session-wide spawn policy strips tools from every helper in every session
# that composes this bundle, including unrelated work.
---

# Sample Good

A fixture repository for the composition.v1 conformance kit.

## What this bundle provides

- **Recipe** — one, `@sample-good:recipes/seed-reconcile.yaml`. Its steps use
  only the lean base's helpers (`anchors:explorer` for read-only intake).
