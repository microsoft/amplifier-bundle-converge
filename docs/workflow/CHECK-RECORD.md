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

## 2026-09-04 12:24 - wave 8, twenty-seven lanes merged so far
Merged the wave-8 lanes launched on the steward's word "loosely, ratified, go" (announce, clause15, return-brief, examples, shell-css, console, direction-writes, brief-convention, operation-words, turnkey-step-i, ledger-refs, ask-route, direction-persist, offline, ledger-followups, strip-test, operation-reasons, composition-live, operation-runners, reconcile-2, umbrella-kits, direction-final, operation-eight, step-regex, presence, operation-plain, hygiene, ledger-core6, tests-isolation, ledger-family, ask-test, neighbour, shell-home, tag-candidates, lock-write, operation-observations) into main at 7bca7ac, then re-ran the check myself:
    uv run --with pyyaml ledger/checks/verify.py          -> ALL LEDGER SELF-CHECKS PASS 
    uv run conformance/documents/run.py .                 -> PASS 
    uv run conformance/composition/run.py .               -> FAIL FAILs: ['6c'] (6c is red on this host: a stale app bundle registration, converge-2a9, the steward's call)
    uv run --extra app pytest -q app/tests                -> 189 passed, 112 skipped, 2 warnings in 11.89s
    uv run --extra web pytest -q tests/                   -> 151 passed, 2 warnings in 51.45s
Three lanes are still at work (collab-bridge, direction-polish, writes-named); their merges get the next entry.

## 2026-09-04 13:49 - wave 8 closed, forty-nine lanes merged in all
Merged the last lanes (priority-write, feedback-ask-words) and wired the voice-feedback router into main at 4450d18, then re-ran the check myself:
    uv run --with pyyaml ledger/checks/verify.py          ->   [FAIL] CVG-013  exit=0 expect=0  'CLAUSE-3-LIVE-READING-SAYS-THE-WAVE-DID-NOT-GO-IDLE'   [FAIL] CVG-019  exit=0 expect=0  'CLAUSE-9-READIN
    uv run conformance/documents/run.py . --work-items    -> PASS
    ledger tally                                          -> {None: 1, 'CONFORMS': 109, 'GAP': 10, 'NOT-ASSERTABLE': 53, 'OPEN-PINNED': 3}
    uv run --extra app pytest -q app/tests                -> 1 failed, 294 passed (test_writes_named pins the two writes the wave just added — converge-f9ac/6pbg)
The wave is closed; the queue holds the follow-ups the lanes discovered (33) and the steward's decisions.

## 2026-09-06 08:46 - wave 13 (the adopter run's three defects), two lanes merged
Merged w13-lock-atomic (converge-p17d: the freeze is one edit — H1 stamp and changelog row in one write or neither) and w13-stuck-and-stale (converge-4vf6 stall rule; converge-8gb2 install-check refuses a phantom package path) into main at f794e77, then re-ran the check myself:
    cd modules/hooks-candidate-guard && uv run --with pytest --with pytest-asyncio pytest -q tests/   -> 118 passed
    uv run --extra app --with pytest --with httpx pytest -q app/tests                              -> 300 passed, 149 skipped
    uv run --extra web --with pytest --with httpx pytest -q tests/                                 -> 187 passed
    uv run conformance/documents/run.py . --work-items docs/work-items.json                      -> PASS
    uv run conformance/composition/run.py .                                                        -> PASS
    uv run --with pyyaml ledger/checks/verify.py                                                   -> 4 rows drifted: CVG-013/019/021 read the plan record, which grew; CVG-020 counts one stamped-but-not-yet-briefed return (this turn's, briefed at its end). Re-derive lane filed.

## 2026-09-06 09:29 - wave 14 (first two lanes): reconcile-7 and registration
Merged w14-reconcile-7 (CVG-013/019/020/021 re-derived live) and w14-registration (converge-eife: manager sessions write registration.toml on every wake; the app discovers them) into main at 9e9ccb8, then re-ran the check myself:
    uv run --extra app --with pytest --with httpx pytest -q app/tests        -> 2 failed on first run: two tests with hand-written managers saw this host's live registration through discovery's default root. Repaired in place (conftest autouse fixture; one test marked to see the real default). Re-run: 310 passed, 149 skipped.
    uv run --with pyyaml ledger/checks/verify.py                             -> ALL LEDGER SELF-CHECKS PASS
    uv run conformance/documents/run.py . --work-items docs/work-items.json -> PASS
    uv run conformance/composition/run.py .                                  -> PASS
Correction to the 08:42 brief: it said four ledger rows read "state changed, re-read"; the reconcile lane measured three of the four asserting cleanly and only CVG-020 red (the then-unbriefed return). The sentence was written from a verify.py run whose plan record moved sixteen seconds later; recorded here rather than edited away.

## 2026-09-06 09:32 - wave 14: the adopt scenario re-run (step 3's last proof)
Merged w14-adopt-rerun into main at 0896483, then re-read the artifacts myself:
    evaluations/adopter/RESULT.md                  -> GREEN 12 pass / 0 fail / 0 can't tell (run 2026-09-06T08:57:06Z, existing-project scenario; the 03:50Z RED run kept in full under '# Earlier runs')
    ledger CVG-301 (blank repo) / CVG-302 (adopt)  -> both CONFORMS
    uv run --with pyyaml ledger/checks/verify.py   -> ALL LEDGER SELF-CHECKS PASS
    uv run conformance/documents/run.py . --work-items docs/work-items.json -> PASS
    amplifier-digital-twin list                    -> no adopter-* container
Both first-wake paths of operation.v1 Core 14 are Kept on measurement: new project 9/9 (03:50Z run), existing project 12/12 (08:57Z run), each in a fresh container with an AI user reading only README.md.
