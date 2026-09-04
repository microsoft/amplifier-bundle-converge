# Sample Bad

A fixture repository for the composition.v1 conformance kit. It violates every
checkable rule at once, so one run surfaces all of them.

VIOLATES 4: nothing in this file says where an automated step's helpers come
from, or which setup makes this repository's step runnable at all. Rule 4 asks
for a single sentence carrying all three halves of composition.v1 Core 4; this
README carries none of them, so a reader installing it cannot tell whether
their own session can run the step. (The wording of the missing sentence is
deliberately not reproduced here — a fixture that quoted it would satisfy the
very rule it is meant to break.)

VIOLATES 5: the shared work queue is named on the root install path
(`bundle.md`) and nowhere else. `behaviors/sample.yaml` — the `--app` install
target — does not include it, so work can be filed after one install and
silently cannot after the other.

VIOLATES 3b: `agents/reader.md` exists on disk and no `agents:` block composes
it, so a live session on this repository never reaches it — and because
`bundle.md` pulls in the heavy package instead of the lean base, that session
reaches no lean-base helper either. Both halves of the live promise fail, and
each is named separately in the verdict.

VIOLATES 6b: the top-level `spawn.exclude_tools` in `bundle.md` is not merely
declared — installed beside an unrelated session it is measured taking that
session's helper's shell, delegation and skills tools away. Rule 6b stands the
unrelated session up twice, once without this repository and once with it, and
reports the difference. This is the 2026-09-02 measurement behind `PINS.md`'s
standing rule, re-taken automatically on every run.

`modules/hooks-candidate-guard/` is an inert, mountable stand-in for the guard,
present for the same reason as in `sample-good`: a bundle whose hook names a
module that is not there cannot be composed at all, and a fixture that cannot be
stood up cannot serve as a negative fixture for the two live rules.
