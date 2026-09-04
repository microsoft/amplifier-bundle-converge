# Superseded kits

A kit here judged a contract that has since been superseded. It is kept for the
record — its rules, its fixtures and its self-test are readable, and its lessons
are cited by the kits that replaced it — but **no live ledger row cites it, and
it is not part of the conformance suite.**

| Kit | Contract it judged | Superseded | By |
|---|---|---|---|
| [`surface/`](surface/) | [`surface.v1`](../../contracts/surface.v1.md) | 2026-09-03 | the experience family — [`experience-direction`](../experience-direction/), [`experience-operation`](../experience-operation/), [`experience-console`](../experience-console/) |

## Why a kit is moved rather than deleted

A superseded kit is the only record of *how a promise used to be checked*. The
three experience kits inherited real machinery from `surface/` — the stdlib HTML
tree, the three-status report shape, the negative-fixture discipline, and the
hard-won rule that a kit must be written against **what the app serves** rather
than what a mockup did (converge-e59). Deleting it would leave those lessons as
prose.

What moving it does change: it stops running. `conformance/pytest.ini` collects
`conformance/`, and the tests under `_superseded/` are excluded there, so a
superseded kit cannot go red against a body it no longer governs.
