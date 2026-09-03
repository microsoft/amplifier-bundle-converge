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
