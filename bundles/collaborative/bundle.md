---
bundle:
  name: converge-collaborative
  version: 0.4.0
  description: Optional complete supervisor host; use the collaborative behavior in an existing host.
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@2c864f7c839c39d4387c41c3bc3f11a7176396da#subdirectory=bundles/anchors/bundle.md
  - bundle: converge:behaviors/collaborative.yaml
---
@anchors:context/system.md
