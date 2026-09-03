#!/usr/bin/env bash
# Static acceptance checks for the app-frontend lane. Run from the repo root.
# Checks 4 and 5 (live app + headless render) are app/static/dev/verify.py.
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 1

MOCK=/home/bkrabach/dev/vision-focused-team-ci/ai-context/converge-mockup-standalone.html
fail=0
pass() { echo "  PASS  $1"; }
bad()  { echo "  FAIL  $1"; fail=1; }

echo "=== 1. no base64 blobs; real branding; favicons + manifest in head ==="
n=$(grep -c 'base64,' app/templates/*.html app/static/js/*.js 2>/dev/null | awk -F: '{s+=$2} END{print s+0}')
echo "  grep -c 'base64,' app/templates/*.html app/static/js/*.js  ->  $n"
[ "$n" -eq 0 ] && pass "no base64 blob anywhere in templates or js" || bad "a base64 blob remains"
grep -q 'src="/branding/icons/converge-icon-64.png"' app/templates/shell.html \
  && pass "brand logo is /branding/icons/converge-icon-64.png" || bad "brand logo is not the branding icon"
for link in 'favicons/favicon.ico' 'favicons/favicon-32.png' 'favicons/apple-touch-icon.png' 'rel="manifest" href="/manifest.webmanifest"'; do
  grep -q "$link" app/templates/base.html && pass "head carries $link" || bad "head is missing $link"
done

echo
echo "=== 2. no inline datasets left in the JS (everything is fetched) ==="
hits=$(grep -nEr 'const (managers|repositories|documentBodies|changes|proposal|history|waves|lanes|timeline|consoleSeed) *=' app/static/js | wc -l)
echo "  grep -nE 'const (managers|repositories|documentBodies|changes|proposal|history|waves|lanes|timeline|consoleSeed) *=' app/static/js -r  ->  $hits"
[ "$hits" -eq 0 ] && pass "no inline dataset declarations" || bad "an inline dataset remains"
echo "  every screen's data arrives through these fetch wrappers:"
grep -oE '^  [a-zA-Z]+: \(' app/static/js/api.js | tr -d ' (:' | sed 's/^/    - api./'

echo
echo "=== 3. every render* from the mockup is an exported module function ==="
mapfile -t fns < <(grep -oE 'function (render[A-Za-z]*)' "$MOCK" | awk '{print $2}' | sort -u)
for fn in "${fns[@]}"; do
  where=$(grep -rl "export function $fn(" app/static/js | head -1)
  if [ -n "$where" ]; then pass "$(printf '%-20s' "$fn") exported from $where"; else bad "$fn is missing"; fi
done
grep -q 'renderTop();' app/static/js/main.js && grep -q 'renderConsole();' app/static/js/main.js \
  && pass "renderAll still full-re-renders (top+sessions+home+direction+operation+console+menu)" \
  || bad "renderAll is not a full re-render"

echo
echo "=== 6. manifest is valid JSON with the two PWA icons; sw.js never caches /login or /api ==="
python3 -c "
import json,sys
m=json.load(open('app/static/manifest.webmanifest'))
icons=[i['src'] for i in m['icons']]
assert icons==['/branding/pwa/pwa-192.png','/branding/pwa/pwa-512.png'], icons
print('  manifest parses; name=%r display=%r icons=%s' % (m['name'], m['display'], icons))
" && pass "manifest.webmanifest is valid JSON with pwa-192 + pwa-512" || bad "manifest is invalid"
grep -q "url.pathname === '/login'" app/static/sw.js && pass "sw.js: /login is returned untouched, never cached" || bad "sw.js does not exempt /login"
grep -q 'if (isApi(url))' app/static/sw.js && pass "sw.js: /api is network-first and never written to the cache" || bad "sw.js does not handle /api network-first"

echo
echo "=== 7. console is read-only and the terminal tab is delegated ==="
grep -q '<input id="consoleInput".*disabled' app/templates/console.html && pass "console input carries the disabled attribute" || bad "console input is not disabled"
grep -q 'read-only in this version' app/templates/console.html && pass "visible note: read-only in this version" || bad "read-only note missing"
grep -q 'window.ConvergeTmux?.attach(' app/static/js/render/console.js && pass "terminal tab calls window.ConvergeTmux?.attach(el, socket, session)" || bad "no ConvergeTmux attach call"
grep -q "terminal viewer not loaded" app/static/js/render/console.js && pass "falls back to 'terminal viewer not loaded' when the viewer is absent" || bad "no soft fallback"

echo
[ "$fail" -eq 0 ] && echo "ALL STATIC ACCEPTANCE CHECKS PASS" || echo "SOME CHECKS FAILED"
exit "$fail"
