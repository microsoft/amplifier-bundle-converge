# Post-merge check record

One entry each time a manager session integrates a wave and re-runs the contract
check itself. `contracts/operation.v1.md` clause 7 says done means the manager
session re-ran the check, and clause 8 says the verification is the manager
session's own and never the worker session's. This file is where that re-run is
written down. Newest last.

**Who writes it.** The manager session, in **its own commit on the integration
branch**, after the merges it covers. A lane never writes an entry here — not to
add one, not to correct one. A lane that believes an entry is wrong says so in
its brief and leaves it to the manager session, the same way it leaves any file
it does not own.

**Why a file of its own.** The other two places a check run leaves a trace —
`ledger/rows.yaml` and `evaluations/turnkey/RESULT.md` — are edited by lanes, so
the newest commit touching either one arrives through a lane merge. Measured on
this repository on 2026-09-04: the turnkey run's attribution step could see that
the integrator had written seven such records before, and still could not say who
verified the newest wave, because the newest record came in on a lane's branch.
A record only the manager session writes removes the confusion at the source.

**The shape of an entry.** A stamped heading, then plain sentences:

```
  ## 2026-09-04 12:40 - wave 8, five lanes merged

  Merged lane/w8-presence, lane/w8-operation-plain, lane/w8-hygiene and
  lane/w8-ledger-core6 into main at be8a5b9, then re-ran the check myself:

      uv run --with pyyaml ledger/checks/verify.py     -> all self-checks pass
      uv run conformance/documents/run.py .            -> 18 kept, 0 broken, 9 can't check

  The documents contract reads Kept. The ledger's own self-checks pass. Nothing
  here was taken from a lane's word for it.
```

Three things make an entry a record rather than a claim, and an entry missing any
of them is worth less than no entry at all:

1. **What it covers** — the merges, by branch or by commit, that this check ran
   after.
2. **The command that was run**, written in backticks or in a block, so a reader
   can run the same thing and compare.
3. **What it printed**, and the plain state word that follows from it — *Kept ·
   Not yet · Broken · Pinned open · Can't check*.

**What an entry proves, and what it does not.** It proves who ran the check: the
commit that adds the entry sits outside every lane merge, so a reader can tell
the manager session's own hand from a lane's. It does not prove the run behind
it was clean, and it does not prove the check covered every merge — those are
answered by re-running the command it names, which is why the command is part of
the entry.

**Everything begins at the first entry.** Waves integrated before this file
existed left no record of who verified them, and nothing here can say. The count
starts below.
