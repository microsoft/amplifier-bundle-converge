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
Converge bundle also loads the shared collaboration guidance through its own
behavior, without the supervisor's tool bindings. The manager mode, guard and
CLI installation path are unchanged.

For a text-only acceptance journey covering negotiation, feedback, observation
failure and role settings, see [the collaborative evaluation](../../evaluations/collaborative/README.md).
Static loading and packaging checks do not prove that live journey passed.

Host-specific presentation, installation, canvas/session binding and model adapters
belong to the consuming integration. Portable packages have no dependency on one.
