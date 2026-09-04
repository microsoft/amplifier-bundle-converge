# experience-collaboration.v1 conformance kit

The runnable definition of **"the seam stays where it is."** Point it at the
companion app — the running server, or a snapshot captured from it — and it
mechanically asserts
[`contracts/experience-collaboration.v1.md`](../../contracts/experience-collaboration.v1.md)
against what the app declares it can reach, and against the repository the app
is a body for.

Stdlib only, and **no browser is launched**.

## Why this kit exists, and what changed with it

This contract had no kit. Five of its ten clauses sat at `NOT-ASSERTABLE` in
[`ledger/rows.yaml`](../../ledger/rows.yaml) — CVG-183, CVG-184, CVG-185,
CVG-187 and (for Core 1) CVG-180 — with the reason "only a live host settles
them".

That is true of **half** of some of them, and the difference is the whole point
of this kit:

| | can a machine settle it? |
|---|---|
| whether a bridge to the host **exists** | **yes** — an absent route is an absent route |
| whether a teammate's reply **came back attributed** | no — that needs a second party on a real host |
| whether whose word counts is **settled at registration** | **yes** — the registration either names a steward or it does not |
| whether a **second person's** word ever reached the record | no — that needs two people on one manager session |

So the checkable halves are now rules that FAIL, and only the halves that
genuinely need a person or a host SKIP — with a reason that names what is
missing and points at the half that is checked.

## The target is a pair

| Half | What it is | Rules that read it |
|---|---|---|
| the app | the running server, or a `--capture` directory | 2, 3, 4a, 5b, 6a, 6b, 8a, 10 |
| the repository | where `app/`, `docs/workflow/` and `contracts/` live | 1, 5a, 7, 9 |

The repository half is **resolved, not passed**, by the convention in
[`../experience/repotarget.py`](../experience/repotarget.py) — shared with the
umbrella kit so the two cannot drift on it. A snapshot with no `repo/` makes
every repository-reading rule SKIP naming the missing half, rather than quietly
judging whatever checkout the kit sits in.

## Run it

```sh
uv run --extra app python -m app.serve --port 8788

export CONVERGE_APP_COOKIE="$(python3 -c "import pathlib;from itsdangerous import \
URLSafeTimedSerializer as S;print(S(pathlib.Path.home().joinpath('.amplifier',\
'converge-app.secret').read_text().strip(), salt='converge-app-session')\
.dumps({'u':'$USER'}))")"

uv run conformance/experience-collaboration/run.py http://127.0.0.1:8788
uv run conformance/experience-collaboration/run.py conformance/experience-collaboration/fixtures/sample-good
```

Output: a JSON report on **stdout**, a human summary on **stderr**, exit **0**
when no rule FAILs and **1** when any does. `--json-only` suppresses the summary.

## What it checks

Rows are numbered to the contract's **Core clause** numbers — rule 7 judges
Core 7 — so a failing rule names the clause it breaks. Where one clause carries
two independent promises the kit emits one row per promise, lettered inside the
clause. **Every one of the ten Core clauses has a row**, and
`test_every_core_clause_has_a_row` fails if one does not.

| # | Clause | The promise this operationalizes | How the kit checks it |
|---|---|---|---|
| 1 | Core 1 | "Git is the protocol; Converge is the lens" | The write path must run `git`, and must not reach the repository through a second transport beside it — a teammate on plain tooling cannot see a private channel. |
| 2 | Core 2 | "Manager sessions never talk to each other directly" | No route addresses a second manager session, and the app's own **code** (docstrings, strings and comments stripped) names no peer, no federation and no other manager as a destination. |
| 3 | Core 3 | "Three origins, one review" | Exactly one review renderer, the origin rendered **as a value**, and no branch that lays a proposal out differently depending where it came from. |
| 4a | Core 4 | "Pull-request comments are a two-way bridge" — that a bridge exists | A route addressing a pull request or its comments, or a code path that posts one. Absent, a steward has to leave and say it somewhere else. |
| 4b | Core 4 | the same clause's other half — the reply comes back attributed | **SKIP.** See below. |
| 5a | Core 5 | "written to the dated ratification record" | The repository holds `docs/workflow/owner-ratifications-<date>.md` **and** the write path names it. |
| 5b | Core 5 | "and posted back to the origin" | Something must address the origin after the word is recorded. Without it a teammate learns the answer only if a person copies it across by hand. |
| 6a | Core 6 | "Inbound changes arrive without you asking for them" | A webhook route, a live stream, or a timer that reloads the project's own data. None of the three means freshness is the steward's job. |
| 6b | Core 6 | "the fallback is named rather than assumed" | The surface must say in plain words how it stays fresh. Where 6a found no mechanism at all, this row says so and cites it — a derived failure, not a second one. |
| 7 | Core 7 | "The manager session is not in the hot path" | The write path must not send a keystroke to a terminal session or open a socket. Any other process a write starts is **named** in the detail rather than passed over. |
| 8a | Core 8 | "One steward per manager session" | The registration must name a steward. Where none does, whose word counts is inferred from whoever is signed in — and the row says who that was. |
| 8b | Core 8 | "no second person's word is written to the record" | **SKIP.** See below. |
| 9 | Core 9 | "A ratification is a change to the repository, made the ordinary way" | The word is recorded, the text is committed, and a proposal takes the repository's own shape — `<document>.vN-candidate.md`, beside the document. |
| 10 | Core 10 | "Converge adds no second collaboration surface" | No route is an issue tracker, a document store or a review tool of its own. A comment **relayed** to the host is rule 4a's bridge, not a surface kept here. |

## The two rules that SKIP, and why

A `SKIP` is never a soft pass.

- **Core 4b** — a comment written by a teammate on a real host, arriving back
  inside the review with their name on it, cannot be produced by any file in
  this tree. What *is* checkable is whether a bridge exists at all: rule 4a.
- **Core 8b** — whether a second person's word ever reached the ratification
  record needs two people answering on one manager session. What *is* checkable
  is whether whose word counts was settled at registration: rule 8a.

`test_skip_set_is_pinned` fails if any other rule drifts into SKIP.

## Three lines this kit is careful about

The contract's clauses pull against each other in three places, and a rule
written carelessly would make a conforming body fail.

### Reaching the host is not reaching another manager

Core 4 **requires** Converge to reach the repository host. Core 2 **forbids** it
reaching another manager session. A rule that banned outbound calls outright
would make the contract self-contradictory. Rule 2 looks for a *peer manager* as
a destination, never for network access as such.

### A word in a comment is not a channel

Rule 2 reported a **fabricated finding** during this kit's build. `app/serve.py`
explains its auth gate with *"There is deliberately no exemption for a loopback
peer."* — and `peer` in that sentence read as a channel to another manager
session in a body that has none. Docstrings, string literals and `#` comments
are now stripped before the source is read, exactly as the direction kit blanks
string literals before reading a handler. `test_a_word_in_a_comment_is_not_a_channel`
keeps it that way.

### A relayed comment is not a second surface

Core 10 forbids Converge **keeping** a tracker; Core 4 requires it **relaying** a
comment to the host. `comment` is deliberately absent from rule 10's
second-surface route set — otherwise the bridge rule 4a asks for would fail
rule 10. `test_a_relayed_comment_is_not_a_second_surface` holds the distinction.

## Fixtures (the kit's own proof)

Both fixtures are a pair — a captured app snapshot plus a `repo/` half.

- `fixtures/sample-good/` — a body that keeps the seam: git as the write path,
  one review whoever proposed, a bridge to the host's pull-request comments, an
  answer that lands in the dated record and returns to its origin, a webhook and
  a plain sentence naming the fallback, one steward per session, and no tracker
  of its own. **PASS on all twelve checkable rules.**
- `fixtures/sample-bad/` — the seam broken every way at once: a peer route
  between manager sessions, a review per origin, no bridge, an answer that goes
  nowhere, freshness left to the steward, writes relayed through a terminal
  session, no steward, and `/api/issues`. **FAIL on all twelve.**

Both are rewritten in place by [`make_fixtures.py`](make_fixtures.py).

## Self-test

```sh
uv run --with pytest pytest conformance/experience-collaboration/tests/ -q
python3 conformance/experience-collaboration/tests/test_conformance.py   # no deps
```

## Measured against the running app

2026-09-04, against `http://127.0.0.1:8823` reading
`vision-focused-team-ci/amplifier-bundle-converge`: **PASS 7 · FAIL 5 · SKIP 2**.

Kept: git is the protocol, no manager reaches another, one review for every
origin, the answer lands in the dated record, no write goes through the manager
session, a ratification is an ordinary commit with a sibling candidate file, and
no second collaboration surface has grown.

The five failures are true findings against a body whose host half is not built:
no bridge to pull-request comments (Core 4), no path returning the answer to its
origin (Core 5), nothing bringing inbound changes in on its own and nothing
naming a fallback (Core 6), and no steward named at registration — the app
answers to whoever is signed in (Core 8).

A FAIL here is a **true finding, not a bug in the kit to be tuned away.** File
it; do not weaken the rule.
