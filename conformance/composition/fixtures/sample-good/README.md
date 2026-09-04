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

Its one helper, `agents/reader.md`, is **composed** into the session by an
`agents:` block in `behaviors/sample.yaml` (composition.v1 Core 3, live half —
rule 3b). Carrying the rulebook is not enough on its own: an agent no `agents:`
block pulls in is discoverable on disk and unreachable from a session, which is
the difference rule 3b stands a real session up to see.

`modules/hooks-candidate-guard/` is an inert, mountable stand-in for the guard.
It exists so this miniature repository can be stood up as a real session at
all — the live rules run against it like any other target. Rules 7a and 7b judge
the guard's *configuration* in `behaviors/sample.yaml`, not its behaviour, so
the stand-in deliberately does nothing.
