# composition.v1 conformance kit

The runnable definition of **"this repository composes leanly."** Point it at a
repository root and it mechanically asserts the conformance list from
[`contracts/composition.v1.md`](../../contracts/composition.v1.md). If it says
PASS, the repository sits on the lean base, its automated steps reach only
lean-base helpers, a real session on it reaches both helper families, an
unrelated session measured beside it keeps its shell, delegation and skills
tools — both beside this working tree and beside the release of it actually
installed on this host — and its guard admits a proposal beside a locked
contract. If it says FAIL, it names the rule, the file, and the line.

## Run it

```sh
uv run conformance/composition/run.py <repo-root>
```

Output: a JSON report on **stdout** and a human summary on **stderr**. Exit code
is **0** when no rule FAILs, **1** when any rule FAILs. Add `--json-only` to
suppress the stderr summary.

```sh
# a conforming repository  ->  VERDICT: PASS, exit 0
uv run conformance/composition/run.py conformance/composition/fixtures/sample-good

# a broken repository      ->  VERDICT: FAIL (twelve rules; 6c declines), exit 1
uv run conformance/composition/run.py conformance/composition/fixtures/sample-bad

# this repository          ->  the real result, whatever it is
uv run conformance/composition/run.py .
```

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 6a judges
Core 6 — so a failing rule names the clause it breaks. Where one clause carries
several independent promises, the kit emits one row per promise, lettered
inside the clause (`1a`, `1b`, …) so a failure names the exact promise rather
than a whole paragraph. **Every one of the seven Core clauses has a row**, and
`test_every_core_clause_has_a_row` fails if one does not.

The kit was numbered to the *Conformance kit asserts* bullets until 2026-09-03,
when the steward ratified the Core-clause anchor
([`docs/workflow/owner-ratifications-2026-09-03.md`](../../docs/workflow/owner-ratifications-2026-09-03.md),
call 2). Under the bullet anchor, four bullets covered seven clauses and Core 3,
4 and 5 had **no row at all** — and a missing row is invisible, because nothing
looks wrong. Rules 4 and 5 below are those rows.

| # | Clause | The contract sentence this operationalizes | How the kit checks it |
|---|---|---|---|
| 1a | Core 1 | "The full foundation package appears nowhere" | Scans every file the bundle loads into a session — `bundle.md`, `behaviors/**`, `context/**` — for `@foundation:`. Reports each hit with file and line. |
| 1b | Core 1 | "Converge assembles its session from the small standard base (the *anchors* bundle …)" | Parses `bundle.md`'s frontmatter and requires an `includes:` entry pointing at `amplifier-foundation .../bundles/anchors/bundle.md`. |
| 2a | Core 2 | "Automated steps use only the lean base's helpers" | Scans every `recipes/**/*.yaml` for a `foundation:`-namespaced helper reference. A step naming one cannot run in a session assembled on the lean base. |
| 2b | Core 2 | the same clause's coverage half | Requires every file under `recipes/` to be named in `bundle.md`. An undeclared step is one nobody reviewed, and one rule 2a scans only by accident. Keeps the step surface exactly what the bundle says it is. |
| 3a | Core 3 | "Its own helpers carry a small local rulebook — stop honestly when a thing cannot be proven; sign commits; cite locations — and borrow nothing else" | Every helper under `agents/` must name a local file that states **all three** rules; that file is the rulebook. The other documents a helper names are domain reading and are not judged — reporting them would be a fabricated finding. "Borrows nothing else" is read as: no helper mentions another bundle's context, which could change under its feet. |
| 3b | Core 3 | the same clause, judged live: a session actually reaches one of Converge's own helpers | Stands up a **real session** on the target's own bundle — `load_and_prepare_bundle` → `create_session` → `initialize()`, the three calls `amplifier tool list -b` makes — and reads the roster it composed. Requires a lean-base helper, one of the repository's own, and a mounted delegation tool. **Reached means composed:** an agent file on disk that no `agents:` block pulls in is discoverable and unreachable, and only a live roster tells the two apart. |
| 4 | Core 4 | "The host requirement is one sentence in the README. Steps can use only helpers present in the session they run in; Converge needs its own full setup or a host on the same lean base." | Reads `README.md`, unwraps block quotes and line wrapping, and requires **one sentence** to carry all three halves: the host, the fact that a step resolves helpers only from the session it runs in, and the lean base. Spread over three paragraphs the requirement is present and unreadable — which is the failure this catches. |
| 5 | Core 5 | "The shared work queue rides on both install paths, so the contract checker can file and read work anywhere." | Requires the work queue to be named on **both** paths: in `bundle.md`'s includes (the root install) and in a `behaviors/*.yaml`'s includes (the `--app` install target). Named on one only, filing work works after one install and silently does not after the other. |
| 6a | Core 6 | "Nothing touches the tools of other work in your session" | Requires no top-level `spawn:` key in `bundle.md`'s frontmatter or in any `behaviors/*.yaml`. A composed `spawn.exclude_tools` strips the named tools from every spawned helper in **every** session that composes the bundle — measured 2026-09-02, including unrelated work. |
| 6b | Core 6 | the same clause, judged live: "After installing Converge beside other work, a helper in an unrelated session keeps its shell, delegation, and skills tools" | Stands up a real **unrelated** session on the lean base alone (the *control*), then the same unrelated session again with this repository installed beside it — once per install path it declares (the *treatments*). The spawned-helper tool surface of each is computed by Amplifier's own `apply_spawn_tool_policy`. PASS when installing takes nothing away. The control is what makes it mean anything: a host may already carry a session-wide spawn policy of its own, and without a baseline the rule would either blame this repository for the host's setting or report green because the tools were gone before it arrived. |
| 6c | Core 6 | the same clause, judged where this repository is **installed**: "After installing Converge beside other work, a helper in an unrelated session keeps its shell, delegation, and skills tools" | Stands up the unrelated session **as this host actually composes it** — the lean base plus the host's whole app-bundle list, exactly as `runtime/config.py` hands `get_app_bundles()` to `load_and_prepare_bundle`. When that session is contaminated, every app entry is loaded alone and asked for its own `spawn`, so the verdict names the entry a user would have to remove. FAIL only when a carrier **names this repository**; a host broken by a foreign bundle is a SKIP naming that bundle, never this repository's failure. |
| 7a | Core 7 | "The guard recognizes both proposal names — `<contract>.vN-candidate.md` and the legacy `CANDIDATE-*.md`" | Reads every `hooks-candidate-guard` config in `behaviors/` and tests its `always_allow_globs` and `candidate_glob` against **both** proposal names — `contracts/CANDIDATE-retry-clause.md` and `contracts/composition.v1-candidate.md`. Both must be admitted by both lists. |
| 7b | Core 7 | "… and refuses every other write to a locked contract" | Compiles the config's `frozen_marker_regex` and tests it against `# Composition Contract — v1 (FROZEN 2026-09-02)` — the H1-parenthetical status form `documents.v1` Core 6 fixes. A regex that misses it leaves a locked contract unguarded. |

### Rule 6c: what the tree does, and what the release already installed does

6a and 6b both judge **this working tree**: 6a that it declares no `spawn:`
key, 6b that composing it onto a neighbour's session takes nothing away. Both
were PASS on 2026-09-04, and both were right. On the same machine, at the same
moment, a *published sibling release of the same product* — app-installed from
another fork — was stripping `tool-bash`, `tool-delegate` and `tool-skills`
from every spawned helper in **every** session on the host, unrelated work
included. That is `converge-w3v`, and it is the gap 6c closes: the tree a
maintainer reads and the release a user runs are different repository states,
and only one of them is what the neighbour actually experiences.

So 6c composes the neighbour's session the way the host really does it, and
when the result is contaminated it loads each app entry alone to find the one
carrying the policy. Two properties keep it honest:

- **It names the entry, not the host.** "Your host is contaminated" is not
  actionable; "remove this URI, which declares `spawn.exclude_tools`" is.
- **It never blames a neighbour's bundle on this repository.** A contaminated
  host whose carrier names no bundle of this repository is a SKIP that says
  the promise is broken *and* says whose setting broke it. This is the same
  discipline rule 6b's control enforces, applied to attribution.

One consequence to expect rather than be surprised by: **6c's verdict is a fact
about the machine, not about the repository.** The same commit can be PASS on a
clean laptop, FAIL on one with a bad release installed, and SKIP on a CI runner
that installs no app bundles at all. That is the promise being asserted — "after
installing Converge beside other work" is a claim about hosts — and it is why
the row always reports the app-bundle count, where the list came from, and which
entry carries the policy. Read a red 6c as "on this machine, right now", and go
read the entry it names.

Because no fixture is installed on anybody's host, 6c declines on both fixtures
by design — so it is proven through a seam instead of a fixture.
`AMPLIFIER_COMPOSITION_KIT_APP_BUNDLES` (whitespace-separated URIs) replaces the
host's app list, and three self-tests drive 6c red, green, and to its
never-blame-a-neighbour decline. A rule that declines everywhere proves as
little as a rule that always passes.

### The live rules (they used to decline; they no longer do)

Rules 3b and 6b are judgments about a **running session**, not about files on
disk. Until 2026-09-04 the kit declined both — `SKIP`, with the reason — and the
self-test pinned the SKIP set to exactly `{3b, 6b}` so neither could drift into
a decline to dodge a failure. That was honest and it was permanent: a rule
guaranteed to skip can never be wrong, and both of these carry the promises that
matter most. The second is the promise behind `PINS.md`'s standing rule — "never
reintroduce a session-wide `spawn:` block" — measured by hand once, on
2026-09-02, and re-taken by nothing for two days.

They now have runners. [`live.py`](live.py) finds the interpreter the installed
`amplifier` CLI runs on and executes [`_live_child.py`](_live_child.py) with it,
one JSON request in, one JSON line out. `run.py` itself still imports nothing
but `pyyaml`. Three sessions are stood up per run (the target, the unrelated
control, and one treatment per install path); on a warm cache the whole kit
takes about a second.

Modules are prepared with `install_deps=False`. What is under test is
**composition** — what lands in a session's mount plan — not whether every
module's Python package installs, and resolving a full dependency closure on
each conformance run would buy no extra signal about either promise.

What did NOT change is the refusal to fabricate. These rules still `SKIP` when a
verdict is genuinely out of reach, and a SKIP names the exact missing capability
from a declared vocabulary (`live.MISSING`): no `amplifier` on PATH, an
interpreter that cannot import `amplifier_app_cli`, a probe that timed out, or
`AMPLIFIER_COMPOSITION_KIT_LIVE=0`. They (with 6c) are also still the **only**
rules allowed to decline at all — `test_only_the_live_rules_may_skip` pins that
ceiling, and `test_live_rules_decline_honestly_when_switched_off` exercises the
decline path so the honest-SKIP behaviour is tested rather than assumed.

Both clauses that carry a live half also carry a file-readable one, and that
half is checked rather than waved at: clause 3's rulebook is rule 3a, clause 6's
absent session-wide policy is rule 6a. The halves catch different things — 6a
proves this repository declares no `spawn:` key, 6b proves that what a
neighbour's session ends up with is unchanged by installing this tree, and 6c
proves the same about the release already installed on the host, which is the
only one of the three a user is actually running.

### Globs are matched properly, not by `fnmatch`

Rule 7a resolves the configured globs itself: `**/` spans zero or more
directories, `*` stays inside one segment, and `[0-9]` is a real character
class. `fnmatch`'s `*` crosses `/` and would silently over-match — reporting a
guard as safe when it is not.

## Fixtures (the kit's own proof)

Both fixtures are miniature repositories that can actually be **stood up as
sessions**, not only read: rules 3b and 6b run against them like any other
target. That is why each carries `modules/hooks-candidate-guard/` — an inert,
mountable stand-in. A bundle whose hook names a module that is not there cannot
be composed at all, and a fixture that cannot be stood up would leave both live
rules unproven. The stand-in is deliberately inert: rules 7a and 7b judge the
guard's **configuration**, read out of `behaviors/sample.yaml`, and a fixture
guard that actually denied writes would fail for reasons unrelated to the
promise under test.

- `fixtures/sample-good/` — a **fully-conforming** miniature repository: the
  lean base in `includes:`, one declared automated step using `anchors:explorer`,
  a helper carrying a local rulebook that states all three rules **and composed
  into the session by an `agents:` block**, a README stating the host requirement
  in one sentence, the work queue named on both install paths, no `spawn:` key,
  and a guard that admits both proposal names and recognizes an H1-parenthetical
  status. The kit reports **PASS** on all twelve file- and session-readable
  rules, and declines the host half (6c) — no fixture is installed on anyone's
  host, so there is no installed release of it to judge.
- `fixtures/sample-bad/` — an **intentionally broken** repository that violates
  every rule at once, so one run surfaces all of them instead of
  stopping at the first: an `@foundation:` reference in loaded context (1a),
  the heavy package instead of the lean base (1b), two steps naming
  `foundation:` helpers (2a), an undeclared `stray-step.yaml` (2b), a helper
  carrying no rulebook and borrowing another bundle's preamble (3a), that same
  helper left out of any `agents:` block so a live session never reaches it, in
  a session with no lean-base helper at all (3b), a README
  that never states the host requirement (4), the work queue on the root
  install path only (5), a top-level `spawn.exclude_tools` (6a) that a live
  unrelated session is measured losing its shell, delegation and skills tools
  to (6b), a guard
  admitting only `CANDIDATE-*.md` (7a), and a frozen-marker regex that only
  recognizes an explicit `**Status:**` field (7b).

  Its `spawn.exclude_tools` names **module ids** (`tool-bash`, `tool-delegate`,
  `tool-skills`), because that is what Amplifier's spawn policy filters on.
  Written as tool names it would look alarming and strip nothing — and a
  fixture that cannot cause the harm it claims cannot serve as rule 6b's
  negative fixture.

Each fixture file carries a comment naming the rule it violates and why, so the
fixture is readable as a worked example of the contract rather than a puzzle.
`sample-bad/README.md` deliberately does **not** quote the sentence clause 4
asks for: a fixture that quoted it would satisfy the very rule it exists to
break.

## Self-test

```sh
uv run --with pytest pytest conformance/composition/tests/ -q
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule the
kit emits must either FAIL on `sample-bad` or be a declared SKIP with a reason.
A rule nobody can make fail proves nothing. As of 2026-09-04 **all twelve**
fixture-judgeable rules FAIL on `sample-bad`, including both live ones. The
thirteenth, 6c, cannot be the subject of a fixture at all — nobody has a fixture
installed on their host — so it is proven through the app-list seam by
`test_host_half_goes_red_when_the_installed_release_strips_tools` and its two
siblings. No rule is exempted from proof, including the one that declines.

`test_every_core_clause_has_a_row` is the one the Core-clause anchor buys: every
numbered clause under `## Core (the teeth)` in `contracts/composition.v1.md`
must have at least one rule row. A clause added to the contract later cannot go
unchecked without this test going red — which is precisely what the bullet
anchor could not do, because under it there was no row to be missing.
