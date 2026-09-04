# Gap analysis — 2026-09-04

What is kept, what is not yet, and what stands between each document and the
steward's lock. Everything below was read from `ledger/rows.yaml` or printed by
a command run on 2026-09-04 against this tree and the app at
`http://127.0.0.1:8788`.

**The four state words** (PROTOCOL §3.3): Kept · Not yet · Pinned open · Can't
check. **The lock bar** (PROTOCOL §5) is four conditions, all of which must hold:
**1** says what it means (the spec is written) · **2** a real example of right and
wrong (a machine-checkable kit with a discriminating good/bad fixture pair) ·
**3** checkable (a real implementation passes it) · **4** steward read and agreed
(a worked example end to end, and the steward stamps it). Every document here is
DRAFT, content owner-ratified 09-02 or 09-03; none is locked, so the stamp is
unmet everywhere and column 4 records the worked-example half.

## Per contract

| Document | Kept | Not yet | Pinned | Can't check | Kit's last verdict | 1 | 2 | 3 | 4 | The one thing standing in the way |
|---|--:|--:|--:|--:|---|:-:|:-:|:-:|:-:|---|
| composition.v1 | 7 | 2 | 0 | 0 | `composition` PASS 10·0·2 | ✓ | ✓ | ✓ | ✓ | Only the stamp: the two skipped rules need a live session, so two bullets are believed, not shown. |
| documents.v1 | 18 | 0 | 1 | 9 | `documents` PASS 18·0·9 | ✓ | ✓ | ✓ | ✓ | Only the stamp — but its own clause 5 is pinned open against it in 8 places (CVG-060). |
| operation.v1 | 2 | 13 | 0 | 0 | turnkey GREEN 9·0·0 exit 0 | ✓ | ✓ | ✗ | ✓ | Condition 3: the harness is green, but no clause row has been re-derived from it, so nothing yet shows a real run keeping any single clause. |
| surface.v1 | 12 | 1 | 0 | 0 | `_superseded/surface` via `tests/` 9 passed | ✓ | ✓ | ✓ | ✓ | Superseded 09-03 by the experience family. Not a lock candidate; build against the family. |
| experience.v1 | 3 | 9 | 0 | 3 | no kit | ✓ | ✗ | ✗ | ✗ | Condition 2: the umbrella's own clauses have no kit at all (converge-f1l). |
| experience-direction.v1 | 4 | 7 | 0 | 0 | `experience-direction` FAIL 6·6·0 | ✓ | ✓ | ✗ | ✗ | Condition 3: six of eleven rules fail against the running app. |
| experience-operation.v1 | 5 | 8 | 0 | 0 | `experience-operation` FAIL 7·8·0 | ✓ | ✓ | ✗ | ✗ | Condition 3: eight of fifteen rules fail against the running app. |
| experience-console.v1 | 7 | 3 | 0 | 0 | `experience-console` FAIL 7·3·0 | ✓ | ✓ | ✗ | ✗ | Condition 3: the pane shows the session but is not it, and it reaches every session on the socket. |
| experience-collaboration.v1 | 5 | 0 | 0 | 5 | no kit | ✓ | ✗ | ✗ | ✗ | Condition 2: no kit, and half its clauses are about git and a person, not this tree. |
| platform-web.v1 | 3 | 5 | 0 | 6 | no kit of its own | ✓ | ✗ | ✗ | ✗ | Condition 2: its rows borrow the three experience kits; nothing asserts the web body's own idioms. |
| platform-ios.v1 | 0 | 0 | 0 | 9 | no kit | ✓ | ✗ | ✗ | ✗ | Condition 2: there is no iOS body to judge. A sub-project, not a lane. |
| platform-android.v1 | 0 | 0 | 0 | 9 | no kit | ✓ | ✗ | ✗ | ✗ | Condition 2: there is no Android body to judge. A sub-project, not a lane. |
| platform-macos.v1 | 0 | 0 | 0 | 9 | no kit | ✓ | ✗ | ✗ | ✗ | Condition 2: there is no macOS body to judge. A sub-project, not a lane. |
| platform-windows.v1 | 0 | 0 | 0 | 9 | no kit | ✓ | ✗ | ✗ | ✗ | Condition 2: there is no Windows body to judge. A sub-project, not a lane. |
| **the vision** (`docs/VISION.md`) | 3 | 0 | 0 | 2 | `documents` rules 2b, 7a, 7b PASS | ✓ | ✓ | ✓ | n/a | Only the stamp. It has no rows of its own: CVG-048, CVG-059, CVG-062 keep it; CVG-049, CVG-063 cannot be settled by a scan. |

**Cross-check, printed** — `python3` tally over `ledger/rows.yaml`:

```
contract                            Kept Not yet  Pinned  Cant check  rows
composition.v1.md                      7       2       0           0     9
documents.v1.md                       18       0       1           9    28
experience-collaboration.v1.md         5       0       0           5    10
experience-console.v1.md               7       3       0           0    10
experience-direction.v1.md             4       7       0           0    11
experience-operation.v1.md             5       8       0           0    13
experience.v1.md                       3       9       0           3    15
operation.v1.md                        2      13       0           0    15
platform-android.v1.md                 0       0       0           9     9
platform-ios.v1.md                     0       0       0           9     9
platform-macos.v1.md                   0       0       0           9     9
platform-web.v1.md                     3       5       0           6    14
platform-windows.v1.md                 0       0       0           9     9
surface.v1.md                         12       1       0           0    13
TOTAL                                 66      48       1          59   175
cross-check OK: 66+48+1+59 = 174 dispositioned rows + 1 SYNC row = 175
```

Fifteen rows above: **fourteen contracts plus the vision** — `contracts/` holds
fourteen files, there is no fifteenth. `uv run --with pyyaml ledger/checks/verify.py` → `ALL LEDGER SELF-CHECKS PASS`, exit 0.

## The announcement, claim by claim

`docs/ANNOUNCEMENT.md` says "publish when every claim below is true." Nine of thirteen are.

| Claim | | What proves it |
|---|---|---|
| Ratified rules for vision, contracts, locking, proposals, deriving work | true | `docs/PROTOCOL.md` v3; `documents` kit PASS 18·0·9 |
| One `--app` install onto an existing Amplifier CLI | true | turnkey step (b), GREEN run F, `evaluations/turnkey/RESULT.md` |
| The manager session derives work from the gap, never files a raw note | true | turnkey step (e): 2 sampled items name a contract and state done |
| Launches worker sessions in isolated lanes | true | turnkey step (f): 2 worktrees, 2 terminal sessions, no outside holder |
| A guard makes locked contracts un-editable | true | `composition` rules 7a, 7b PASS |
| Composed from proven pieces; one install brings them up or says what is missing | true | turnkey step (c): install check green, 8 present, 0 unchecked |
| Direction — vision and contracts as one experience, questions, proposals | true | `experience-direction` rules 1, 2, 4, 7, 8 PASS |
| Operation — brief, plan, lanes, evidence, limits, feedback | true | `experience-operation` rules 1, 2a, 6, 9, 10, 12 PASS |
| At most five things ever ask for your word | true | `experience-direction`/`-operation` needs rules PASS; ledger CVG-104 is the umbrella half, not yet |
| Whether each contract is kept, shown in Direction | not yet | CVG-105; `experience-direction` FAIL 6·6·0 |
| Whatever you can do in the app, the manager session can do too | not yet | CVG-107 — nothing asserts it, and no kit covers the umbrella |
| Judges completion by evidence, integrates, verifies, re-checks | not yet | CVG-017, CVG-018 — the turnkey run is green but the clause rows still cite a finished item |
| **"Four writes in total"** | not yet, and wrong | `experience.v1` §4 says *exactly five*. The app answers seven non-auth write routes today and offers neither *raise or lower a priority* nor *ask*. Three numbers, no two alike. |

## The grouping — every not-yet row, to exactly one item

48 rows are Not yet. Every one already had a live item as its named fix; what
the queue lacked was the row ids written down. They are now, by cause and
component.

<details><summary>Row ids → item — 48 rows, 11 items, none twice</summary>

*Record — the ledger itself (16 rows)*
- **converge-0gb** — fifteen rows name a fix already finished; the harness that
  would settle them is green, so each needs re-deriving from a live run —
  CVG-008, CVG-009, CVG-011, CVG-012, CVG-013, CVG-014, CVG-015, CVG-016,
  CVG-017, CVG-018, CVG-019, CVG-021, CVG-022, CVG-023, CVG-038
- **converge-823** — nothing records that a return happened — CVG-020

*Contracts — the umbrella disagrees with its family (1 row)*
- **converge-d3n** — `experience.v1` §15 names two contracts that never existed
  — CVG-114

*The app, Direction (10 rows)*
- **converge-6cc** — two of the five writes are absent: the edit route landed
  but nothing offers it, and Ask exists nowhere — CVG-103, CVG-124, CVG-128,
  CVG-129, CVG-200
- **converge-wrx** — restore and the per-change choices show a message and
  forget — CVG-125, CVG-127
- **converge-jdm** — no lock gate, one copy control where the clause names two,
  no zoom — CVG-122, CVG-130, CVG-201

*The app, Operation (10 rows)*
- **converge-q66** — lane words, flow measures, queue numbers and steering are
  short of the contract — CVG-100, CVG-105, CVG-144, CVG-146, CVG-147, CVG-150,
  CVG-152
- **converge-lwa** — the plan, the brief and the timeline do not carry their
  reasons or their parts — CVG-141, CVG-142, CVG-143

*The app, Console and offline (6 rows)*
- **converge-tfu** — the pane shows the session but is not it, is not resizable
  when wide, and reaches every session on the socket — CVG-162, CVG-163,
  CVG-169, CVG-205
- **converge-719** — offline the shell loads and every payload is empty —
  CVG-209, CVG-210

*Conformance — the umbrella has no kit (5 rows)*
- **converge-f1l** — the umbrella's own clauses are asserted by nothing —
  CVG-104, CVG-107, CVG-108, CVG-112, CVG-113
</details>

**Newly filed, because nothing owed them yet:** `converge-41l`, the
announcement's write count (above); and `converge-str` — ten of fourteen
contracts have no worked example, so condition 4 cannot be met for any of them.

**Kept and listed, owning no not-yet row:** `converge-6qk` (the header strip is
cut off at every width — a measured failure of the clause CVG-213 cannot
check); `converge-a5r` and `converge-h5k`, whose conditions no longer hold (9a
now reads *all 66 work items name a contract and define done*; the retired-kit
import passes 9 tests). A steward closes those two, not this lane.

## Not work: honestly unmeasurable today

59 rows are Can't check. **None became an item** — none names a way to make it checkable today.

- **36 rows** — `platform-ios`, `-android`, `-macos`, `-windows`, nine each. No
  body to judge. These alone have a concrete path — build the body — so four
  items are filed and **deferred**, reason *sub-project: its own repo, steward,
  and converge instance*: `converge-ftp` iOS · `converge-1ul` Android ·
  `converge-xej` macOS · `converge-36z` Windows. Not lanes here.
- **9 rows, documents.v1** — CVG-040, CVG-049, CVG-058, CVG-063, CVG-065,
  CVG-067, CVG-068, CVG-069, CVG-070. Each needs a reader, not a scan.
- **6 rows, platform-web.v1** — CVG-202, CVG-203, CVG-204, CVG-206, CVG-207,
  CVG-213. Layout judgments. CVG-213 (renders at 390 and 1280 with nothing cut
  off) has a visible path — a rendered-width harness — and `converge-6qk` is a
  real failure measured against it by hand.
- **5 rows, experience-collaboration.v1** — CVG-180, CVG-183, CVG-184, CVG-185,
  CVG-187. About git, a pull request, and a person.
- **3 rows, experience.v1** — CVG-109, CVG-110, CVG-111. What IDIOM means.

**One row is Pinned open**: CVG-060 — `documents.v1` §5 asks for one to three
plain lines of why, and 8 of 43 clauses run past three. Not an item: it is a
steward's call on the clause, not a lane's work.

## The plan

Waves run in order, items inside a wave at the same time, no two owning a path.

**Wave 1 — the record and the direction. No app code.**

| Item | Owns | Why here |
|---|---|---|
| converge-0gb | `ledger/**` | Fifteen not-yet rows name a finished fix; the harness is green, so this is the cheapest truth to recover, and everything downstream reads the ledger. |
| converge-41l | `docs/ANNOUNCEMENT.md` | The public text says four writes where the contract says five; a wrong number is cheap now and expensive after publishing. |
| converge-str | `docs/examples/**` | Ten contracts cannot meet the lock bar's fourth condition until one exists; nothing is blocked on it, so it fills spare width. |
| converge-d3n | `contracts/experience.v1-candidate.md` | The only wrong statement inside a ratified contract. It is a steward decision, so start it early and let it wait on a person, not on a lane. |
| converge-823 | `modes/converge-manager.md`, `docs/workflow/OWNER-RETURN-LOG.md` | Half the clause is already kept; the other half needs a steward's reading, which is faster than a build. |

**Wave 2 — the app, one area each.**

| Item | Owns | Why here |
|---|---|---|
| converge-6cc | `app/static/js/render/direction.js`, `app/templates/` | Two of the five writes are missing; the routes landed and the controls did not, so this is the largest single move toward the umbrella. |
| converge-q66 | `app/data.py`, `app/static/js/render/operation.js` | Seven rows, one cause — the payloads carry the wrong words and the missing numbers. |
| converge-tfu | `app/tmux_view.py`, `app/static/js/console.js`, `app/static/css/console.css` | Independent of the other two views, and one of its three parts is a reach the app should not have. |
| converge-6qk | `app/static/css/shell.css` | One CSS rule, measured at four widths, and it touches nothing else. |

**Wave 3 — the second pass over the same two files.**

| Item | Owns | Why here |
|---|---|---|
| converge-wrx | `app/static/js/render/direction.js` | **Collision** with converge-6cc (wave 2), same file. It waits rather than merges. |
| converge-lwa | `app/data.py` | **Collision** with converge-q66 (wave 2), same file. It waits rather than merges. |
| converge-719 | `app/static/sw.js`, `app/static/js/api.js` | Offline is a design call about which payloads may be cached with a visible time; it collides with nothing. |

**Wave 4 — the last pass, and the kits.**

| Item | Owns | Why here |
|---|---|---|
| converge-jdm | `app/static/js/render/direction.js`, `app/templates/` | **Collision** with converge-6cc and converge-wrx, same file. Third of three, so it lands last. |
| converge-f1l | `conformance/experience/**`, `conformance/experience-collaboration/**` | Written after the app moves, so the kit judges the body that shipped rather than the one that was planned. |

**Not scheduled — deferred:** `converge-ftp`, `converge-1ul`, `converge-xej`, `converge-36z` — each its own repo, steward, and converge instance, no lane here.
