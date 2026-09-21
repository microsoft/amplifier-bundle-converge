# Collaborative supervisor

Add portable supervision to an existing host with the behavior:

```sh
amplifier bundle add 'git+https://github.com/microsoft/amplifier-bundle-converge@<reviewed-commit>#subdirectory=behaviors/collaborative.yaml' --app
```

Replace the placeholder with a reviewed full commit. The behavior owns no provider,
root instruction, session orchestrator, skills list or host API. Installed Create,
Direction and Operations capabilities and a separately configured native manager
remain prerequisites; an instruction bundle does not provision them.

This directory remains an optional **complete** Anchors-based supervisor profile.
Select it deliberately as a root, never as a behavior. Both entry points use the
same [packaged context](../../packages/collaborative/README.md). The original root
Converge bundle, manager mode and CLI installation path are unchanged.

Host-specific presentation, installation, canvas/session binding and model adapters
belong to the consuming integration. Portable packages have no dependency on one.
