# Worked examples

One file per contract, showing that contract carried end to end — from a
sentence in `contracts/` to a check that was actually run, with its output
printed. This is the fourth condition of the lock bar in
[`../PROTOCOL.md`](../PROTOCOL.md) §5:

> 4. A worked example exists end-to-end.

An example here is not a tutorial and not a demo. It quotes the promise, runs
the check that decides it, shows a target the check passes and a target it
refuses, and states plainly what the check does **not** cover. Where a clause
cannot be settled today it says Can't check and says why — never a quiet pass.

## The fourteen contracts

| Contract | Worked example | Notes |
|---|---|---|
| [`composition.v1`](../../contracts/composition.v1.md) | [`composition.md`](composition.md) | |
| [`documents.v1`](../../contracts/documents.v1.md) | [`documents.md`](documents.md) | |
| [`operation.v1`](../../contracts/operation.v1.md) | [`operation.md`](operation.md) | |
| [`experience.v1`](../../contracts/experience.v1.md) | [`experience.md`](experience.md) | the umbrella; borrows its evidence from the family kits |
| [`experience-direction.v1`](../../contracts/experience-direction.v1.md) | [`experience-direction.md`](experience-direction.md) | |
| [`experience-operation.v1`](../../contracts/experience-operation.v1.md) | [`experience-operation.md`](experience-operation.md) | |
| [`experience-console.v1`](../../contracts/experience-console.v1.md) | [`experience-console.md`](experience-console.md) | |
| [`experience-collaboration.v1`](../../contracts/experience-collaboration.v1.md) | [`experience-collaboration.md`](experience-collaboration.md) | checked against this repository's own git history |
| [`platform-web.v1`](../../contracts/platform-web.v1.md) | [`platform-web.md`](platform-web.md) | the only body that exists; runs a real browser at 390 and 1280 |
| [`platform-ios.v1`](../../contracts/platform-ios.v1.md) | **none yet** | no body exists to work an example through |
| [`platform-android.v1`](../../contracts/platform-android.v1.md) | **none yet** | no body exists to work an example through |
| [`platform-macos.v1`](../../contracts/platform-macos.v1.md) | **none yet** | no body exists to work an example through |
| [`platform-windows.v1`](../../contracts/platform-windows.v1.md) | **none yet** | no body exists to work an example through |
| [`surface.v1`](../../contracts/surface.v1.md) | [`surface.md`](surface.md) | superseded 2026-09-03 by the experience family; kept for the record |

## The four with no example, and why

`platform-ios.v1` · `platform-android.v1` · `platform-macos.v1` ·
`platform-windows.v1` have **no worked example, and cannot have one yet**. The
reason is the same for all four and it is not neglect:

**There is no body to work an example through.** A platform contract is entirely
about the shape a behaviour takes in one body — a pane or a sheet, a bottom bar
or a rail, a widget or a menu-bar item. With no iOS app, no Android app, no
macOS app and no Windows app, there is nothing to point a check at, so an
"example" could only be a description of a screen nobody has built. Writing one
would put a fabricated screenshot where evidence belongs.

The ledger already says the same thing, row by row: all **36** rows across those
four contracts (nine each) are Can't check. None is a gap owed by a lane, and
none is a quiet pass.

Each has a filed work item, deferred with the reason *sub-project: its own repo,
steward, and converge instance* — `converge-ftp` iOS · `converge-1ul` Android ·
`converge-xej` macOS · `converge-36z` Windows. When a body exists, its example
is written the same way `platform-web.md` was, and this table's *none yet* row
becomes a link.

Until then these four contracts cannot meet the lock bar's fourth condition, and
they are not candidates for locking. That is the honest reading, and it is the
one this file records.

## Reading one

The six examples added on 2026-09-04 — the experience family and
`platform-web` — follow the same order, so they can be compared. The four
written earlier (`composition`, `documents`, `operation`, `surface`) tell the
same story as a narrative walkthrough instead:

1. **The contract**, linked, and the check that decides it.
2. **One promise**, quoted in full from the contract's Core.
3. **Right and wrong, told apart** — a target the check passes and a target it
   refuses, both run.
4. **The same check against the real body**, with its output.
5. **What the check does not claim** — the sentence that keeps a green run from
   meaning more than it does.
6. **Clause traceability** — every Core clause, how it is checked, and its state
   today in plain words: Kept · Not yet · Broken · Pinned open · Can't check.

## Running them yourself

The three experience kits and `platform-web.md` read a running app. Serve it,
mint a cookie with the app's own signer, and point the kits at it:

```sh
uv run --extra app python -m app.serve --host 127.0.0.1 --port 8788
export CONVERGE_APP_COOKIE="…"   # see conformance/README.md
uv run conformance/experience-direction/run.py http://127.0.0.1:8788
uv run conformance/experience-operation/run.py http://127.0.0.1:8788
uv run conformance/experience-console/run.py  http://127.0.0.1:8788
```

`composition.md`, `documents.md` and `experience-collaboration.md` read the
repository itself and need no app.

The runs printed in these files were made on **2026-09-04** against this
repository at **`f718a20`**, with the app served on port 8811. A later run may
differ — that is the point of a check — so re-run rather than trusting the
transcript.
