#!/usr/bin/env python3
"""Headless verification of the Converge front-end against the dev stub.

Same approach as docs/presentation/verify.py: drive a real Chromium, assert no
horizontal overflow and no console errors, and write one screenshot per view.

    python3 app/static/dev/stub_server.py --port 8799 &
    python3 app/static/dev/verify.py

Exits non-zero if anything fails. Screenshots land in app/static/dev/screenshots/.
"""
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8799"
DEV = pathlib.Path(__file__).resolve().parent
SHOTS = DEV / "screenshots"

VIEWPORTS = [("1280", 1280, 720), ("390", 390, 844)]

OVERFLOW_JS = """
() => {
  const de = document.documentElement;
  // An element inside a deliberately scrollable/clipped container (the mobile
  // session rail, the raw view) cannot push the PAGE sideways — only elements
  // whose every ancestor lets content out can.
  const clipped = (el) => {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll' || ox === 'hidden') return true;
    }
    return false;
  };
  let widest = null, wmax = 0;
  document.querySelectorAll('#app *').forEach(el => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (clipped(el)) return;
    if (r.right > wmax) { wmax = r.right; widest = (el.id || el.className || el.tagName); }
  });
  return {
    docScrollW: de.scrollWidth, docClientW: de.clientWidth,
    bodyScrollW: document.body.scrollWidth,
    rightMost: Math.round(wmax), rightMostEl: String(widest).slice(0, 70),
  };
}
"""

results = []
failures = []


def check(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": detail})
    if not ok:
        failures.append(f"{name}: {detail}")
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{('  — ' + detail) if detail else ''}")


def shoot(page, label, view):
    # let any transient toast clear so the screenshot shows the layout, not a banner
    try:
        page.wait_for_function(
            "() => document.getElementById('toast').classList.contains('hidden')", timeout=4000)
    except Exception:
        pass
    path = SHOTS / f"{label}-{view}.png"
    page.screenshot(path=str(path), full_page=False)
    return path


def overflow(page, label, view):
    m = page.evaluate(OVERFLOW_JS)
    slack = 1
    ok = m["docScrollW"] <= m["docClientW"] + slack and m["rightMost"] <= m["docClientW"] + slack
    check(f"[{view}] no horizontal overflow on {label}", ok,
          f"scrollW={m['docScrollW']} clientW={m['docClientW']} rightMost={m['rightMost']} ({m['rightMostEl']})")


def boot_page(ctx, errors):
    page = ctx.new_page()
    page.on("console", lambda msg: errors.append(f"console.{msg.type}: {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))
    page.goto(BASE, wait_until="networkidle")
    page.wait_for_function("() => document.querySelectorAll('#sessionList .session-card').length > 0")
    page.wait_for_function("() => document.getElementById('docTitle').textContent.trim().length > 1")
    return page


def run_view(browser, view, width, height):
    print(f"\n=== viewport {width}x{height} ===")
    errors = []
    narrow = width <= 980  # below this the console is a sheet over the workspace
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = boot_page(ctx, errors)

    # --- console is open on boot and shows the tmux delegation notice ---
    closed = page.evaluate("() => document.querySelector('.body-grid').classList.contains('console-closed')")
    check(f"[{view}] console open on boot", not closed)
    body = page.text_content("#consoleBody")
    check(f"[{view}] terminal tab degrades to 'terminal viewer not loaded'", "terminal viewer not loaded" in body, body.strip()[:60])
    check(f"[{view}] console input is disabled", page.get_attribute("#consoleInput", "disabled") is not None)
    check(f"[{view}] read-only note visible", "read-only in this version" in page.text_content(".console-footer"))
    page.click('[data-console-tab="notes"]')
    page.wait_for_selector("#consoleBody .context-note")
    check(f"[{view}] console Context tab shows the manager's own objective",
          "convincing stakeholder demo" in page.text_content("#consoleBody"))
    shoot(page, "console-open", view)
    overflow(page, "console-open", view)
    page.click('[data-console-tab="terminal"]')
    if narrow:
        page.click("#consoleClose")  # the sheet covers the workspace on a phone

    # --- Direction (read) ---
    title = page.text_content("#docTitle").strip()
    check(f"[{view}] boots into Direction with a fetched document", title == "Amplifier Core Vision", f"docTitle={title!r}")
    check(f"[{view}] document body rendered from the API", "thin runtime" in page.text_content("#documentModeContent"))
    shoot(page, "direction-read", view)
    overflow(page, "direction-read", view)

    # --- picking another document fetches it, and "N need your word" navigates back
    #     to whichever document /api/needs names ---
    page.click('[data-doc="kernel"]')
    page.wait_for_function("() => document.getElementById('docPath').textContent.includes('kernel')")
    check(f"[{view}] selecting another document fetches it",
          page.text_content("#docTitle").strip() == "Kernel Contract", page.text_content("#docPath"))
    page.click("#needsYouButton")
    page.wait_for_selector(".review-sheet")
    check(f"[{view}] 'need your word' opens the document named by /api/needs",
          "#42" in page.text_content(".review-hero") and "VISION.md" in page.text_content("#docPath"),
          page.text_content("#docPath"))

    # --- Direction (review) ---
    page.click('[data-doc-mode="review"]')
    page.wait_for_selector(".review-sheet")
    check(f"[{view}] review sheet renders the fetched proposal", "#42" in page.text_content(".review-hero"))
    shoot(page, "direction-review", view)
    overflow(page, "direction-review", view)

    # --- Operation ---
    page.click("#operationTab")
    page.wait_for_selector("#lanesGrid .lane-card")
    lanes = page.eval_on_selector_all("#lanesGrid .lane-card", "els => els.length")
    check(f"[{view}] operation lanes fetched", lanes == 6, f"{lanes} lane cards")
    check(f"[{view}] waves fetched", page.eval_on_selector_all("#wavesGrid .wave-card", "els => els.length") == 3)
    shoot(page, "operation", view)
    overflow(page, "operation", view)

    # --- console state persists across the workspace switch ---
    def is_closed():
        return page.evaluate("() => document.querySelector('.body-grid').classList.contains('console-closed')")

    if not is_closed():
        page.click("#consoleToggle")
    check(f"[{view}] console closes", is_closed())
    page.click("#directionTab")
    check(f"[{view}] closed console stays closed across a workspace switch", is_closed())
    page.click("#consoleToggle")  # reopen
    check(f"[{view}] console reopens", not is_closed())
    page.click("#operationTab")
    check(f"[{view}] reopened console stays open across a workspace switch", not is_closed())
    page.click("#directionTab")
    if narrow:
        page.click("#consoleClose")

    # --- Home ---
    page.click("#brandHome")
    page.wait_for_selector("#homeSessionGrid .home-manager-card")
    cards = page.eval_on_selector_all("#homeSessionGrid .home-manager-card", "els => els.length")
    check(f"[{view}] home lists every manager from /api/boot", cards == 3, f"{cards} cards")
    shoot(page, "home", view)
    overflow(page, "home", view)

    # --- back into a manager from home ---
    page.click("#homeSessionGrid .home-manager-card")
    page.wait_for_selector("#directionView:not(.hidden), #operationView:not(.hidden)")
    check(f"[{view}] selecting a manager from home returns to the workspace",
          page.evaluate("() => document.getElementById('homeView').classList.contains('hidden')"))

    check(f"[{view}] no console errors", not errors, "; ".join(errors[:3]))
    ctx.close()


def run_decisions(browser):
    print("\n=== decision posts (1280x720) ===")
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = boot_page(ctx, errors)
    posted = []
    page.on("request", lambda r: posted.append(f"{r.method} {r.url}") if r.method == "POST" else None)

    page.click('[data-doc-mode="review"]')
    page.wait_for_selector(".review-sheet")

    for value in ["ratified", "declined", "later"]:
        page.click(f'[data-decision="{value}"]')
        page.wait_for_selector(".decision-status")
        page.wait_for_timeout(150)

    # ratify-with-edits routes through the dialog first
    page.click('[data-decision="ratified-with-edits"]')
    page.wait_for_selector("#appDialog[open]")
    page.fill("#ratifyEdit", "Say 'observable by default' rather than 'observable'.")
    page.click("#dialogActions button:nth-child(2)")
    page.wait_for_timeout(400)

    decision_posts = [p for p in posted if p.endswith("/decision")]
    check("four decision buttons each POST /api/managers/{mid}/decision", len(decision_posts) == 4,
          f"{len(decision_posts)} POSTs: {decision_posts}")
    check("no console errors during decisions", not errors, "; ".join(errors[:3]))
    ctx.close()


def run_actions(browser):
    print("\n=== steer / fill lanes / feedback (1280x720) ===")
    errors = []
    ctx = browser.new_context(viewport={"width": 1280, "height": 720})
    page = boot_page(ctx, errors)
    posted = []
    page.on("request", lambda r: posted.append(r.url.split("/")[-1]) if r.method == "POST" else None)

    page.click("#operationTab")
    page.wait_for_selector("#fillLanesButton")
    page.click("#fillLanesButton")
    page.wait_for_timeout(400)
    check("Fill lanes POSTs /steer", posted.count("steer") == 1, str(posted))

    page.click("#steerButton")
    page.wait_for_selector("#appDialog[open]")
    page.fill("#steerNote", "Hold the noon deadline.")
    page.click("#dialogActions button:nth-child(2)")
    page.wait_for_timeout(500)
    check("Steer dialog POSTs /steer", posted.count("steer") == 2, str(posted))

    page.click("#timelineButton")
    page.wait_for_selector("#timelineCard:not(.hidden) .timeline-entry")
    entries = page.eval_on_selector_all("#timelineList .timeline-entry", "els => els.length")
    check("Timeline opens with fetched entries", entries == 4, f"{entries} entries")
    page.click("#closeTimelineButton")

    page.click("#directionTab")
    page.click("#feedbackButton")
    page.wait_for_selector("#appDialog[open]")
    page.fill("#feedbackText", "The lane cards wrap oddly on my phone.")
    page.click("#dialogActions button:nth-child(2)")
    page.wait_for_timeout(500)
    check("Feedback dialog POSTs /feedback", posted.count("feedback") == 1, str(posted))

    check("no console errors during actions", not errors, "; ".join(errors[:3]))
    ctx.close()


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    for old in SHOTS.glob("*.png"):
        old.unlink()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for view, w, h in VIEWPORTS:
            run_view(browser, view, w, h)
        run_decisions(browser)
        run_actions(browser)
        browser.close()

    (DEV / "verify-report.json").write_text(json.dumps(
        {"results": results, "failures": failures,
         "screenshots": sorted(x.name for x in SHOTS.glob("*.png"))}, indent=2) + "\n")
    print(f"\n{len(results) - len(failures)}/{len(results)} checks passed; "
          f"{len(list(SHOTS.glob('*.png')))} screenshots in {SHOTS}")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
