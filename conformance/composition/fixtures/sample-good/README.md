# Sample Good

A fixture repository for the composition.v1 conformance kit. It conforms.

## Install

**The behavior path (`--app`):** composes the capability payload onto whatever
bundle is already active.

**The full-workspace path:** composes the root `bundle.md`, which assembles on
the lean `anchors` base.

> **Host requirement (composition.v1 Core 4, and rule 4's positive fixture).**
> An automated step resolves its helpers only from the session it runs in, so
> running this repository's step needs either this repository's own
> full-workspace setup or a host session already on the lean `anchors` base.

Both paths pull in the shared work queue (composition.v1 Core 5): `bundle.md`
names the `work-tracker` behavior, and `behaviors/sample.yaml` — the `--app`
install target — includes it as well, so filing work is possible after either
install.
