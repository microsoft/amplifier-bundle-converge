#!/usr/bin/env python3
"""Headless verification for the explainer (index.html).

Adapted from docs/presentation/verify.py, which verifies the deck.

Checks: section count and shape (h2 claim + bold takeaway + h3 sub-beats),
a visual in every section, alt text on every image, the body-text word budget,
sticky-nav highlighting via IntersectionObserver, no horizontal overflow at
1280x800 and 390x844, no console errors, and no network dependencies.
Writes one screenshot per section at 1280 to screenshots/.

    python3 docs/presentation/explainer/verify.py
"""

import json
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
PAGE = HERE / "index.html"
SHOTS = HERE / "screenshots"

WORD_BODY_JS = """
() => {
  const strip = root => {
    const c = root.cloneNode(true);
    c.querySelectorAll('h1,h2,h3,.eyebrow,.kicker,.fig-title,figcaption,svg,.sub')
      .forEach(n => n.remove());
    return (c.innerText || c.textContent || '')
      .replace(/\\s+/g, ' ').trim().split(' ').filter(w => /[A-Za-z0-9]/.test(w));
  };
  const per = [];
  document.querySelectorAll('main section').forEach(s => {
    per.push({ id: s.id || 'hero', words: strip(s).length });
  });
  const all = (document.body.innerText || '')
    .replace(/\\s+/g, ' ').trim().split(' ').filter(w => /[A-Za-z0-9]/.test(w));
  return { per, body: strip(document.querySelector('main')).length, visible: all.length };
}
"""

SHAPE_JS = """
() => Array.from(document.querySelectorAll('main section')).map(s => ({
  id: s.id || 'hero',
  h2: (s.querySelector('h2') || {}).innerText || '',
  h3: s.querySelectorAll('h3').length,
  takeaway: !!s.querySelector('.takeaway b, .first p b'),
  img: s.querySelectorAll('img').length,
  svg: s.querySelectorAll('svg').length,
  composed: s.querySelectorAll('.devices,.stack,.chips,.panel,pre.codeline').length,
  altless: Array.from(s.querySelectorAll('img')).filter(i => !i.alt || !i.alt.trim()).length,
}))
"""

OVERFLOW_JS = """
() => {
  const de = document.documentElement;
  let widest = null, wmax = 0;
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > wmax) { wmax = r.right; widest = el.className || el.tagName; }
  });
  return {
    docScrollW: de.scrollWidth, docClientW: de.clientWidth,
    bodyScrollW: document.body.scrollWidth,
    rightMost: Math.round(wmax), rightMostEl: String(widest).slice(0, 60),
  };
}
"""


def main() -> int:
    SHOTS.mkdir(exist_ok=True)
    for old in SHOTS.glob("*.png"):
        old.unlink()

    raw = PAGE.read_text()
    url = PAGE.as_uri()
    problems: list[str] = []
    report: dict = {}

    # ---- static checks (no network deps, vocabulary, leaks) ----
    net = len(re.findall(r'(?:src|href)="https?://', raw))
    allowed = len(re.findall(
        r'href="https?://(?:www\.)?w3\.org', raw))  # xmlns is an attribute, not a fetch
    report["network_refs"] = net
    if net:
        problems.append(f"{net} network references (src/href http) found; expected 0")
    banned = re.findall(r"(?i)frozen|attention steward", raw)
    report["banned_terms"] = banned
    if banned:
        problems.append(f"banned vocabulary present: {sorted(set(w.lower() for w in banned))}")
    del allowed

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        page = browser.new_page(viewport={"width": 1280, "height": 800})
        errors: list[str] = []
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}")
                if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("request", lambda r: errors.append(f"network: {r.url}")
                if r.url.startswith("http") else None)
        page.goto(url, wait_until="networkidle")

        # ---- words ----
        words = page.evaluate(WORD_BODY_JS)
        report["words"] = words
        if words["body"] > 2000:
            problems.append(f"body text {words['body']} words (>2000)")

        # ---- shape ----
        shape = page.evaluate(SHAPE_JS)
        report["sections"] = shape
        content = [s for s in shape if s["id"] != "hero"]
        report["section_count"] = len(content)
        if not 7 <= len(content) <= 9:
            problems.append(f"section count {len(content)} outside 7-9")
        for s in shape:
            if s["img"] + s["svg"] + s["composed"] == 0:
                problems.append(f"section {s['id']} has no visual")
            if s["altless"]:
                problems.append(f"section {s['id']} has {s['altless']} img without alt")
            if not s["takeaway"]:
                problems.append(f"section {s['id']} has no bold takeaway")
            if s["id"] != "hero" and not s["h2"].strip():
                problems.append(f"section {s['id']} has no h2")
            if s["id"] != "hero" and s["h3"] == 0:
                problems.append(f"section {s['id']} has no h3 sub-beat")

        # ---- nav: anchors present for every section, aria-current tracks scroll ----
        nav = page.evaluate("""() => {
          const links = Array.from(document.querySelectorAll('.topbar nav a'));
          const ids = Array.from(document.querySelectorAll('main section[id]')).map(s => s.id);
          return { hrefs: links.map(a => a.getAttribute('href')), ids: ids };
        }""")
        report["nav"] = nav
        for i in nav["ids"]:
            if "#" + i not in nav["hrefs"]:
                problems.append(f"no nav anchor for section {i}")

        current: list[str] = []
        page.evaluate("document.documentElement.style.scrollBehavior = 'auto'")
        for sid in nav["ids"]:
            page.evaluate(f"document.getElementById('{sid}').scrollIntoView()")
            page.wait_for_timeout(400)
            cur = page.evaluate(
                "() => { const a = document.querySelector('.topbar nav a[aria-current]');"
                " return a ? a.getAttribute('href') : null; }")
            current.append(f"{sid}->{cur}")
            if cur != "#" + sid:
                problems.append(f"nav highlight wrong at {sid}: got {cur}")
        report["nav_highlight"] = current
        report["progress_after_scroll"] = page.evaluate(
            "() => document.getElementById('pbar').style.width")

        # ---- no-JS behaviour: anchors still resolve ----
        nojs = browser.new_context(java_script_enabled=False, reduced_motion="reduce")
        p3 = nojs.new_page()
        p3.set_viewport_size({"width": 1280, "height": 800})
        p3.goto(url, wait_until="load")
        nav_links = p3.locator(".topbar nav a").count()
        sections_seen = p3.locator("main section[id]").count()
        p3.locator('.topbar nav a[href="#start"]').click()
        p3.wait_for_timeout(600)
        landed = p3.locator("#start").bounding_box()
        report["nojs"] = {
            "title": p3.title(),
            "nav_links": nav_links,
            "sections": sections_seen,
            "anchor_scrolled_to_start": bool(landed and abs(landed["y"]) < 200),
        }
        if not p3.title() or nav_links != sections_seen:
            problems.append(f"no-JS render incomplete: {report['nojs']}")
        if not report["nojs"]["anchor_scrolled_to_start"]:
            problems.append(f"no-JS anchor navigation failed: {report['nojs']}")
        p3.close()
        nojs.close()

        # ---- layout at both viewports + screenshots ----
        for label, w, h, shoot in (("1280x800", 1280, 800, True), ("390x844", 390, 844, False)):
            p2 = browser.new_page(viewport={"width": w, "height": h})
            errs: list[str] = []
            p2.on("console", lambda m, e=errs: e.append(f"console.{m.type}: {m.text}")
                  if m.type == "error" else None)
            p2.on("pageerror", lambda ex, e=errs: e.append(f"pageerror: {ex}"))
            p2.goto(url, wait_until="networkidle")
            p2.evaluate("document.documentElement.style.scrollBehavior = 'auto'")
            rows = []
            for sid in ["hero"] + nav["ids"]:
                sel = "section.hero" if sid == "hero" else f"#{sid}"
                p2.eval_on_selector(sel, "el => el.scrollIntoView()")
                p2.wait_for_timeout(220)
                m = p2.evaluate(OVERFLOW_JS)
                m["section"] = sid
                m["h_overflow"] = m["docScrollW"] > m["docClientW"] + 1
                rows.append(m)
                if m["h_overflow"]:
                    problems.append(
                        f"[{label}] {sid} horizontal overflow: "
                        f"scrollW={m['docScrollW']} clientW={m['docClientW']} "
                        f"rightmost={m['rightMost']} ({m['rightMostEl']})")
                if shoot:
                    n = 0 if sid == "hero" else nav["ids"].index(sid) + 1
                    p2.locator(sel).screenshot(path=str(SHOTS / f"section-{n:02d}-{sid}.png"))
            report[f"layout_{label}"] = rows
            report[f"console_{label}"] = errs
            if errs:
                problems.append(f"[{label}] console errors: {errs}")
            p2.close()

        net_reqs = [e for e in errors if e.startswith("network:")]
        report["network_requests"] = net_reqs
        if net_reqs:
            problems.append(f"page made {len(net_reqs)} network requests: {net_reqs[:3]}")
        report["console_main"] = [e for e in errors if not e.startswith("network:")]
        if [e for e in errors if e.startswith("pageerror") or "console.error" in e]:
            problems.append(f"console errors: {report['console_main']}")
        browser.close()

    report["problems"] = problems
    (HERE / "verify-report.json").write_text(json.dumps(report, indent=1))

    print(f"sections: {report['section_count']} (plus hero)")
    print(f"words: body={report['words']['body']}  all-visible={report['words']['visible']}")
    print("per section:", ", ".join(f"{s['id']}:{s['words']}" for s in report["words"]["per"]))
    print("nav highlight:", ", ".join(report["nav_highlight"]))
    print("screenshots:", len(list(SHOTS.glob("*.png"))))
    print("network requests:", len(report["network_requests"]))
    if problems:
        print(f"\nPROBLEMS ({len(problems)}):")
        for p in problems:
            print("  -", p)
        return 1
    print("\nALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
