#!/usr/bin/env python3
"""Headless check of the running app, at a phone width and a desktop width.

Same approach as docs/presentation/verify.py: drive a real browser, look for
sideways overflow and browser errors, and write one screenshot per screen.

    python3 poc/verify.py --url http://127.0.0.1:8098

Screens: the home list, Direction (reading, changes, review), Operation, and
the console pane open — then the same pane still open after switching places,
which is the pair that shows it survives the toggle.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"

WIDTHS = (("phone", 390, 844), ("desktop", 1280, 900))

OVERFLOW_JS = """
() => {
  const de = document.documentElement;
  let widest = null, wmax = 0;
  document.querySelectorAll('.shell *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.right > wmax) { wmax = r.right; widest = el.className || el.tagName; }
  });
  return {
    docScrollW: de.scrollWidth, docClientW: de.clientWidth,
    bodyScrollW: document.body.scrollWidth,
    rightMost: Math.round(wmax), rightMostEl: String(widest).slice(0, 70),
  };
}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8098")
    args = parser.parse_args()

    SHOTS.mkdir(exist_ok=True)
    for old in SHOTS.glob("*.png"):
        old.unlink()

    report: dict = {"url": args.url, "screens": [], "errors": [], "overflow": []}

    with sync_playwright() as play:
        browser = play.chromium.launch()
        for label, width, height in WIDTHS:
            page = browser.new_page(viewport={"width": width, "height": height})
            errors: list[str] = []
            page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

            def shot(name: str, note: str = "") -> None:
                page.wait_for_timeout(320)
                path = SHOTS / f"{label}-{name}.png"
                page.screenshot(path=str(path), full_page=False)
                measured = page.evaluate(OVERFLOW_JS)
                over = measured["docScrollW"] > measured["docClientW"] + 1
                report["screens"].append({
                    "width": label, "screen": name, "file": path.name,
                    "note": note, "overflow": over, "measured": measured,
                })
                if over:
                    report["overflow"].append(f"{label}/{name}: {measured}")

            page.goto(args.url, wait_until="networkidle")
            page.wait_for_selector("#cards button")
            shot("1-home", "the list of manager sessions")

            page.click("#cards button")
            page.wait_for_selector(".doc")
            shot("2-direction-reading", "the vision, read")

            page.click("text=Changes")
            page.wait_for_selector("#doc-panel .tag")
            shot("3-direction-changes", "what changed since the last saved version")

            page.click("text=Review")
            page.wait_for_selector("#doc-panel .block")
            shot("4-direction-review", "a proposal, answered with a word")

            page.click(".place[data-place='operation']")
            page.wait_for_selector("#operation .block")
            shot("5-operation", "the manager session at work")

            page.click(".place[data-place='direction']")
            page.wait_for_selector(".doc, #doc-panel .block")
            page.click("#console-toggle")
            page.wait_for_selector("body.console-open")
            page.wait_for_timeout(700)
            open_in_direction = page.evaluate("() => document.body.classList.contains('console-open')")
            shot("6-direction-console-open", "the console pane, open beside Direction")

            page.click(".place[data-place='operation']")
            page.wait_for_selector("#operation .block")
            page.wait_for_timeout(320)
            open_in_operation = page.evaluate("() => document.body.classList.contains('console-open')")
            has_text = page.evaluate(
                "() => (document.getElementById('tray-screen').innerText || '').includes('manager')"
            )
            shot("7-operation-console-open", "the same pane, still open after switching places")

            report["screens"].append({
                "width": label, "screen": "console-survives-the-toggle",
                "open_in_direction": open_in_direction,
                "open_in_operation": open_in_operation,
                "pane_has_content": has_text,
                "pass": bool(open_in_direction and open_in_operation and has_text),
            })
            if not (open_in_direction and open_in_operation):
                report["errors"].append(f"{label}: the console pane did not survive the toggle")

            report["errors"].extend(f"{label}: {e}" for e in errors)
            page.close()
        browser.close()

    (SHOTS / "verify-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    ok = not report["errors"] and not report["overflow"]
    print(f"screens captured : {len([s for s in report['screens'] if 'file' in s])}")
    print(f"sideways overflow: {len(report['overflow'])}")
    for line in report["overflow"]:
        print("   " + line)
    print(f"browser errors   : {len(report['errors'])}")
    for line in report["errors"]:
        print("   " + line)
    for screen in report["screens"]:
        if screen.get("screen") == "console-survives-the-toggle":
            print(f"console survives the toggle ({screen['width']}): "
                  f"{'PASS' if screen['pass'] else 'FAIL'} "
                  f"(open in Direction={screen['open_in_direction']}, "
                  f"open in Operation={screen['open_in_operation']}, "
                  f"pane has content={screen['pane_has_content']})")
            ok = ok and screen["pass"]
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
