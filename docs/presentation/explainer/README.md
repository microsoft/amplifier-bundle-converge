# Amplifier Converge — the explainer

`index.html` is one self-contained file. No server, no network, no build.

**Open it.** Double-click the file, or `open`/`xdg-open` it. Everything (CSS, JS, images) is
inline. About twelve minutes of reading; deep-link a section with `#operation`. The sticky
section nav highlights where you are, and falls back to plain anchors with JavaScript off.

**How it relates to the deck.** `../amplifier-converge.html` is the six-minute walk-through;
this is the sit-down companion — same palette, type stacks, vocabulary and claims, one
presented and one read. Where wording differs, `docs/ANNOUNCEMENT.md` and the contracts are
canonical. Both link onward from the Sources footer.

**Which announcement claim each section carries** (`docs/ANNOUNCEMENT.md`):

| # | Section | Claim |
|---|---|---|
| — | Read this first | "You define what must be true. It builds toward it — with you, over time." |
| 01 | Why now | Why now — one amplified person; coordination cannot keep pace |
| 02 | Three roles | The idea — manager session, worker sessions, you are the intent steward |
| 03 | Two documents | The idea — vision and contracts; "the direction is grown, not declared" |
| 04 | Through-line | One text, two audiences — the unbroken through-line |
| 05 | What you do | What you do — attention only where irreplaceable; the four calls |
| 06 | The operation | What ships — the queue, the plan, lanes, evidence, the brief, feedback |
| 07 | The app | What ships — two places; five things at most; four writes; no data of its own |
| 08 | What it is not | What this is not, and what it depends on |
| 09 | Getting started | Getting started — the one install line, reproduced verbatim |

**Image provenance.** The five photographic illustrations are the deck's own AI-generated,
textless images, copied unchanged into `assets/` (`hero-day`, `hero-roles`, `hero-grown`,
`hero-throughline`, `hero-lanes`) and embedded as base64 so the page stays one file. Every
diagram is hand-built inline SVG; the two interface concepts are hand-built HTML/CSS. No new
images were generated. The UX mockup screenshots were **not** used: they carry superseded
vocabulary in the pixels.

**Verify.** `python3 docs/presentation/explainer/verify.py` re-runs every check — section shape,
body-word budget, a visual and alt text per section, sticky-nav highlighting, no-JS anchors,
layout at 1280 and 390, console errors, zero network requests — and rewrites `screenshots/`
(one per section at 1280). `verify-report.json` is its last run.
