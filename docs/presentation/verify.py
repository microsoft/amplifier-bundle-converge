#!/usr/bin/env python3
"""Headless verification for amplifier-converge.html.

Checks: no horizontal overflow / vertical clipping at 1280x720 and 390x844,
no console errors, per-slide word budget, keyboard + TL;DR + notes behaviour,
and writes one screenshot per slide at 1280x720.

    python3 docs/presentation/verify.py
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
DECK = HERE / "amplifier-converge.html"
SHOTS = HERE / "screenshots"

WORD_JS = """
() => {
  const out = [];
  document.querySelectorAll('.slide').forEach((s, i) => {
    const c = s.cloneNode(true);
    c.querySelectorAll('h1,h2,aside.notes,svg title,.cover__hint').forEach(n => n.remove());
    const words = (c.innerText || c.textContent || '')
      .replace(/\\s+/g, ' ').trim().split(' ').filter(w => /[A-Za-z0-9]/.test(w));
    const head = s.querySelector('h1,h2');
    out.push({ n: i + 1, id: s.id, words: words.length,
               head: head ? head.innerText.trim().slice(0, 60) : '',
               text: words.join(' ') });
  });
  return out;
}
"""

OVERFLOW_JS = """
() => {
  const de = document.documentElement;
  const cur = document.querySelector('.slide.is-current');
  const inner = cur.querySelector('.slide__in');
  let widest = null, wmax = 0;
  cur.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.right > wmax) { wmax = r.right; widest = el.className || el.tagName; }
  });
  return {
    docScrollW: de.scrollWidth, docClientW: de.clientWidth,
    bodyScrollW: document.body.scrollWidth,
    innerScrollH: inner ? inner.scrollHeight : 0,
    innerClientH: inner ? inner.clientHeight : 0,
    rightMost: Math.round(wmax), rightMostEl: String(widest).slice(0, 60),
  };
}
"""


def main() -> int:
    SHOTS.mkdir(exist_ok=True)
    for old in SHOTS.glob("*.png"):
        old.unlink()

    url = DECK.as_uri()
    problems: list[str] = []
    report: dict = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        # ---- words (measured once, layout-independent) ----
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        errors: list[str] = []
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.goto(url, wait_until="networkidle")

        words = page.evaluate(WORD_JS)
        report["words"] = words
        report["max_words"] = max(w["words"] for w in words)
        report["slide_count"] = len(words)
        if report["slide_count"] < 14 or report["slide_count"] > 18:
            problems.append(f"slide count {report['slide_count']} outside 14-18")
        for w in words:
            if w["words"] > 20:
                problems.append(f"slide {w['n']} body = {w['words']} words (>20): {w['text']}")

        # every slide has a visual
        vis = page.evaluate("""() => Array.from(document.querySelectorAll('.slide')).map(s => ({
            n: s.id,
            img: s.querySelectorAll('img').length,
            svg: s.querySelectorAll('svg:not(.wordmark__seal)').length,
            composed: s.querySelectorAll('.devices,.stack,.chips,.codeline').length,
            altless: Array.from(s.querySelectorAll('img')).filter(i => !i.alt || !i.alt.trim()).length,
        }))""")
        report["visuals"] = vis
        for v in vis:
            if v["img"] + v["svg"] + v["composed"] == 0:
                problems.append(f"slide {v['n']} has no visual")
            if v["altless"]:
                problems.append(f"slide {v['n']} has {v['altless']} img without alt")

        # ---- behaviour ----
        beh = {}
        page.keyboard.press("End")
        beh["end"] = page.evaluate("deckState()")
        page.keyboard.press("Home")
        beh["home"] = page.evaluate("deckState()")
        page.keyboard.press("ArrowRight")
        page.keyboard.press("ArrowRight")
        beh["right_twice"] = page.evaluate("deckState()")
        page.keyboard.press("ArrowLeft")
        beh["left_once"] = page.evaluate("deckState()")
        page.keyboard.press("t")
        beh["tldr_on"] = page.evaluate("deckState()")
        page.keyboard.press("ArrowRight")
        beh["tldr_next"] = page.evaluate("deckState()")
        page.keyboard.press("End")
        beh["tldr_end"] = page.evaluate("deckState()")
        page.keyboard.press("Escape")
        beh["tldr_off"] = page.evaluate("deckState()")
        page.keyboard.press("n")
        beh["notes_on"] = page.evaluate("deckState()")
        beh["notes_visible"] = page.evaluate(
            "() => { const n = document.querySelector('.slide.is-current .notes');"
            " return n ? getComputedStyle(n).display : 'none'; }")
        beh["notes_count"] = page.evaluate(
            "() => document.querySelectorAll('.slide aside.notes').length")
        page.keyboard.press("n")
        beh["notes_off"] = page.evaluate("deckState()")
        # click navigation
        page.evaluate("deckGo(1)")
        page.mouse.click(1100, 400)
        beh["click_right"] = page.evaluate("deckState()")
        page.mouse.click(120, 400)
        beh["click_left"] = page.evaluate("deckState()")
        # tldr button
        page.evaluate("deckGo(2)")
        page.click("[data-act='tldr-on']")
        beh["tldr_button_from_slide2"] = page.evaluate("deckState()")
        page.click("[data-act='tldr-off']")
        beh["tldr_button_off"] = page.evaluate("deckState()")
        beh["progress_after"] = page.evaluate(
            "() => document.getElementById('hudFill').style.width")
        report["behaviour"] = beh

        # ---- layout at both viewports + screenshots ----
        for label, w, h, shoot in (("1280x720", 1280, 720, True), ("390x844", 390, 844, False)):
            p2 = browser.new_page(viewport={"width": w, "height": h})
            errs: list[str] = []
            p2.on("console", lambda m, e=errs: e.append(f"console.{m.type}: {m.text}")
                  if m.type == "error" else None)
            p2.on("pageerror", lambda ex, e=errs: e.append(f"pageerror: {ex}"))
            p2.goto(url, wait_until="networkidle")
            rows = []
            for i in range(1, report["slide_count"] + 1):
                p2.evaluate(f"deckGo({i})")
                p2.wait_for_timeout(140)
                m = p2.evaluate(OVERFLOW_JS)
                m["slide"] = i
                m["h_overflow"] = m["docScrollW"] > m["docClientW"] + 1
                m["v_scroll_needed"] = m["innerScrollH"] > m["innerClientH"] + 1
                rows.append(m)
                if m["h_overflow"]:
                    problems.append(
                        f"[{label}] slide {i} horizontal overflow: "
                        f"scrollW={m['docScrollW']} clientW={m['docClientW']} "
                        f"rightmost={m['rightMost']} ({m['rightMostEl']})")
                if m["v_scroll_needed"]:
                    problems.append(
                        f"[{label}] slide {i} content taller than frame: "
                        f"{m['innerScrollH']} > {m['innerClientH']}")
                if shoot:
                    p2.screenshot(path=str(SHOTS / f"slide-{i:02d}.png"))
            report[f"layout_{label}"] = rows
            report[f"console_{label}"] = errs
            if errs:
                problems.append(f"[{label}] console errors: {errs}")
            p2.close()

        report["console_main"] = errors
        if [e for e in errors if e.startswith("pageerror") or "console.error" in e]:
            problems.append(f"console errors: {errors}")
        browser.close()

    report["problems"] = problems
    (HERE / "verify-report.json").write_text(json.dumps(report, indent=1))

    print(f"slides: {report['slide_count']}   max body words: {report['max_words']}")
    print("word counts:", ", ".join(f"{w['n']}:{w['words']}" for w in report["words"]))
    print("screenshots:", len(list(SHOTS.glob('*.png'))))
    print("behaviour:", json.dumps(report["behaviour"], indent=1))
    if problems:
        print(f"\nPROBLEMS ({len(problems)}):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
