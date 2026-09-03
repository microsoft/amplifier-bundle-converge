# The lumen gap fixture

A tiny repository with **two planted gaps, in two files that do not touch**.
It is the input the turnkey harness derives work from — the "sample gap" in
`operation.v1`'s turnkey sentence.

```
gap-repo/
  contracts/lumen.v1.md   one LOCKED contract, two Core clauses, two asserts
  src/readings.py         gap 1 lives here: panel_temperature names no unit
  src/report.py           two public entry points
  docs/INDEX.md           gap 2 lives here: render_summary is not named
  check.py                the repository's OWN conformance kit
answer-key.json           what the gaps are, who owns which file, what done means
seed.sh                   materialize gap-repo into a target dir as a git repo
```

## Why two gaps, and why in different files

`operation.v1` clause 6: **width is a collision decision.** Lanes fill only with
items that provably touch different files; adjacent items run as one lane.

So a fixture with one gap could never justify two lanes, and a fixture with two
gaps in the *same* file would have to run them as one. Two gaps in two files
that do not touch is the smallest fixture that makes "run two lanes" the correct
answer rather than an arbitrary one. `tests/test_turnkey.py` asserts that
disjointness, so the fixture cannot quietly drift into a colliding pair.

## The gaps

| Rule | Clause | Quote | Owns | Done means |
|---|---|---|---|---|
| 1 | 1 | "Every reading names its unit." | `src/readings.py` | `check.py` rule 1 reports PASS |
| 2 | 2 | "Every public entry point is named in the index." | `docs/INDEX.md` | `check.py` rule 2 reports PASS |

Both quotes appear verbatim in `contracts/lumen.v1.md`; a test asserts that too,
so the answer key cannot describe a contract the fixture does not have.

## Its own kit is red on purpose

```console
$ cd gap-repo && python3 check.py .
  [FAIL] 1 units: 1 reading(s) name no unit in src/readings.py: panel_temperature.
  [FAIL] 2 index: 1 public entry point(s) in src/report.py are absent from docs/INDEX.md: render_summary.
  VERDICT: FAIL (pass=0 fail=2 skip=0)
$ echo $?
1
```

A fixture that has quietly healed would let a turnkey run report success without
anything having been done. `test_the_fixture_is_red_before_any_work` and
`test_the_answer_key_matches_what_the_fixture_actually_says` exist to catch that.

## Seeding

```console
$ ./seed.sh /tmp/lumen
/tmp/lumen
0ebab226f9aac59368e72882707ac305c4742eaf
```

`seed.sh` refuses a non-empty target rather than mixing two working trees, and
`main` is the base every lane branches from. Non-zero exit with the reason on
stderr is what the harness records as the seeding step's evidence.
