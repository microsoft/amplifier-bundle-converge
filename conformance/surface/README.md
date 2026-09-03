# surface.v1 conformance kit

The runnable definition of **"the companion page keeps its promises."** Point it
at the page — an HTML file, or a directory holding `index.html` — and it
mechanically asserts the conformance list from
[`contracts/surface.v1.md`](../../contracts/surface.v1.md).

Stdlib only, and **no browser is launched**.

## What a static check buys, and what it does not

A static structural check can prove the parts of an interaction exist and are
**wired to one another**: that the repair card's answer reaches the gauge, that
the lock control is disabled while a condition is amber, that the diff view has
a removed sentence to show. That is a real assertion — a promise wired to
nothing fails it, loudly, naming the missing half.

It cannot prove an interaction *behaves* when a person taps it, and it cannot
judge a render. Those rows report:

    SKIP — the app is not built yet (converge-2qh)

never a fabricated PASS. When the app exists, those rows are exactly what a live
harness closes.

## Run it

```sh
uv run conformance/surface/run.py <index.html | dir>
```

Output: a JSON report on **stdout** and a human summary on **stderr**. Exit code
is **0** when no rule FAILs, **1** when any rule FAILs. Add `--json-only` to
suppress the stderr summary.

```sh
# a conforming page  ->  VERDICT: PASS, exit 0
uv run conformance/surface/run.py conformance/surface/fixtures/sample-good

# a broken page      ->  VERDICT: FAIL (all eight checkable rules), exit 1
uv run conformance/surface/run.py conformance/surface/fixtures/sample-bad

# the verified mockup (read-only reference) -> the real result, whatever it is
uv run conformance/surface/run.py \
  /home/bkrabach/dev/vision-focused-team-ci/ai_working/converge-ux-mockups/index.html
```

## What it checks

Rows are numbered to the contract's **Conformance kit asserts** bullets. Bullet
1 names five separate interactions, so it gets five rows — a failure names the
exact interaction rather than the whole sentence.

| # | The contract sentence this operationalizes | How the kit checks it |
|---|---|---|
| 1a | "Places switch" | Every element classed `screen` is a place; every `data-goto` value must resolve to one; and the script must read `data-goto` and mark the active place. A navigation control pointing at a place that does not exist is the failure this catches. |
| 1b | "answering marks the card and shortens the list" | Requires `[data-answer]` controls, a `#needCount`, a handler that marks the card `is-answered`, and a handler that **decrements** `#needCount`. Marking without decrementing leaves the strip the same length. |
| 1c | "fill updates the gauge and the board" | Requires `#gauge` and `#gaugeLabel`, a `fillLanes` routine that reaches the gauge, an answer control carrying `data-effect="fill"`, and the handler that routes one to the other. This is the wiring that turns detection into repair. |
| 1d | "the lock control stays off until all four are green" | Extracts the `#readiness` block by counting its own open/close tags, and requires **exactly four** conditions, at least one marked not-green, and a lock control carrying `disabled`. |
| 1e | "what-changed shows removed sentences" | Requires `#diffBtn`, a handler toggling the diff view, and at least one `<del>`. Additions alone cannot answer "was anything dropped?", which is the whole reason the view exists. |
| 2 | "Renders at 390 and 1280 pixels with nothing cut off and no console errors" | **SKIP** — needs a live browser render at two widths; the app is not built yet (converge-2qh). |
| 3a | "Exactly four write paths" | Requires all four families present: answer with a word (`[data-answer]`), raise or lower a priority (`[data-signal]`), drop feedback (`#sendDrop`/`#dropBox`), steer (`#fillBtn`/`#targetSel`/budget/`#tellAllBtn`). |
| 3b | "each mapped to a named manager-session operation" | **SKIP** — the mapping lives in the running system, not the markup; the app is not built yet (converge-2qh). |
| 4 | "Every answer lands in the dated ratification record" | Requires a `#filedList` and an answer handler that writes the word and what it answered into it. Checks that an answer **has somewhere to land**; that the record is durable and dated is part of the running system. |
| 5 | "No internal vocabulary outside Details folds" | Scans the app's **own words** for terms a colleague who is not an engineer would have to look up — ledger, reconcile, recipe, bundle, orchestrator, YAML, stdout, frontmatter, and the rest. Reports the term and the sentence it appeared in. |

### Rule 5 scans the app's own words, and says so

Two spans of text are deliberately **out of scope**, and the kit reports how
much of each it set aside:

- **Text inside a `<details>` fold** — that is precisely where the contract
  says technical detail belongs.
- **Text inside a rendered project document** (`.doc` / `.docpane`) — a
  contract's own prose is that *document's* responsibility, checked by the
  `documents.v1` kit. Scanning it here would report a contract's vocabulary as
  an app defect.

The scanner also skips a term that sits inside a longer hyphenated token:
`amplifier-bundle-converge` in a header chip is a project's **name**, not the
word "bundle" used as jargon. A trailing full stop does **not** earn that
exemption — "filed against the ledger." is jargon, plainly, and is reported.
Both behaviours are covered by their own test, because each is a place a
careless scanner would invent a finding or miss a real one.

### The two SKIPs are honest, and pinned

The self-test pins the SKIP set to exactly `{2, 3b}` and asserts each reason
names the work that closes it — so a rule cannot quietly drift into SKIP to
dodge a failure, and nobody reading a report has to guess what is missing.

## Fixtures (the kit's own proof)

- `fixtures/sample-good/` — a **conforming** companion page: three places with
  resolving navigation, an answer handler that stamps the card, decrements the
  strip and files the word, a repair card whose answer reaches the gauge, a
  four-condition lock with the control disabled, a diff carrying a removal, all
  four write paths, and its technical detail behind a Details fold. The kit
  reports **PASS** on all eight checkable rules.
- `fixtures/sample-bad/` — an **intentionally broken** page where the promised
  interactions are markup with nothing behind them: one place and a dangling
  navigation target (1a), no `#needCount` and no answer handler (1b), no gauge
  and no fill wiring (1c), three all-green conditions and a live lock control
  (1d), a diff with only additions (1e), three of four write paths absent (3a),
  nowhere for an answer to land (4), and internal vocabulary in the card copy
  (5).

Each fixture carries a comment naming the rule it violates and why, so the
fixture reads as a worked example of the contract rather than a puzzle.

## Self-test

```sh
uv run --with pytest pytest conformance/surface/tests/ -q
```

`test_every_rule_has_a_negative_fixture` is the load-bearing one: every rule the
kit emits must either FAIL on `sample-bad` or be a declared SKIP with a reason.
A rule nobody can make fail proves nothing.
