#!/usr/bin/env bash
#
# Run the Converge app beside this checkout. One command, nothing else to know.
#
#     scripts/run-app.sh
#
# It serves HTTPS on the LAN by default, prints the URL, says how you sign in
# and how to trust the certificate, and says where it looked for manager
# sessions. Ctrl-C stops it.
#
# Why a wrapper at all, when `uv run --extra app python -m app.serve` is one line
# already: that line has to be typed from the repository root, needs `--extra
# app` to be remembered, and says nothing about how to get in once it is up. A
# reader who has just started their first manager session should not have to
# know any of that. `composition.v1` Core 5 is the same idea for the install
# command; this is it for the app.
#
# Two decisions worth naming, and both are the user's explicit direction
# (converge-b2ak), not a convenience default that happened to land here:
#
#   --host 127.0.0.1   loopback only, for the SSH-tunnel case -- forward a
#                       local port over ssh and open it as if it were local.
#                       Everything else defaults to every interface (0.0.0.0),
#                       because the whole point of this app is a phone or a
#                       teammate's laptop reaching it on the LAN, and a default
#                       that has to be undone every time is not a default.
#   --port N            serve somewhere other than 8788. Use this when 8788 is
#                       already taken -- by the service in
#                       `app/converge-app.service`, or by another checkout.
#
# HTTPS is not a flag: it is always on, using a small local certificate
# authority this app creates on first run (`app/tls.py`). There is no
# `--no-tls` -- a mode that quietly served plain HTTP would undo the one thing
# this app promises: a password never crosses the network unencrypted, on the
# loopback tunnel case or the LAN case alike. `/setup` on the printed URL says
# how to trust the certificate, or how to click through the warning safely.
#
# Anything else is handed to `app.serve` untouched (`--config`, `--state`,
# `--tls-dir`).
set -euo pipefail

HOST=0.0.0.0
PORT=8788
PASS_THROUGH=()

usage() {
    cat <<'USAGE'
Run the Converge app beside this checkout.

    scripts/run-app.sh [--host ADDR] [--port N] [-- ...args for app.serve]

  --host ADDR   bind this address instead of 0.0.0.0 (every interface).
                Pass --host 127.0.0.1 for the loopback/SSH-tunnel case.
  --lan         accepted for backward compatibility -- binding every
                interface is now the default, so this flag changes nothing
  --port N      serve on N instead of 8788
  -h, --help    this

HTTPS is always on (a local CA + leaf certificate app/tls.py manages); there
is no plain-HTTP mode. Anything else is passed to `python -m app.serve`
unchanged, so `--config PATH`, `--state PATH` and `--tls-dir PATH` work as
they do there. Ctrl-C stops the server.
USAGE
}

while [ $# -gt 0 ]; do
    case "$1" in
        --lan)
            # No-op: every interface is already the default. Kept so an
            # existing habit or script does not start erroring on an
            # unrecognised flag the moment this default changed.
            shift
            ;;
        --port)
            if [ $# -lt 2 ]; then
                echo "run-app.sh: --port needs a number" >&2
                exit 2
            fi
            PORT="$2"
            shift 2
            ;;
        --port=*)
            PORT="${1#*=}"
            shift
            ;;
        --host)
            if [ $# -lt 2 ]; then
                echo "run-app.sh: --host needs an address" >&2
                exit 2
            fi
            HOST="$2"
            shift 2
            ;;
        --host=*)
            HOST="${1#*=}"
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        --)
            shift
            while [ $# -gt 0 ]; do
                PASS_THROUGH+=("$1")
                shift
            done
            ;;
        *)
            PASS_THROUGH+=("$1")
            shift
            ;;
    esac
done

case "$PORT" in
    '' | *[!0-9]*)
        echo "run-app.sh: --port takes a number, not '${PORT}'" >&2
        exit 2
        ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
    cat >&2 <<'NOUV'
run-app.sh: `uv` is not on this machine, and it is what runs the app.

Install it, then run this again:

    curl -LsSf https://astral.sh/uv/install.sh | sh

(https://docs.astral.sh/uv/getting-started/installation/ carries the other ways.)
NOUV
    exit 1
fi

if [ "$HOST" = "0.0.0.0" ]; then
    OPEN="https://$(hostname):${PORT}"
    ALSO="  also:     https://127.0.0.1:${PORT} (on this machine)"
else
    OPEN="https://${HOST}:${PORT}"
    ALSO="  network:  bound to ${HOST} only -- drop --host to open it to this network"
fi

echo "Converge app -- from ${ROOT}"
echo "  open:     ${OPEN}"
echo "${ALSO}"
echo "  sign in:  your account on $(hostname) -- the username and password you log in"
echo "            with, checked by PAM. The app keeps no passwords."
echo "  trust:    the certificate is signed by a local CA this app made on first run --"
echo "            visit ${OPEN}/setup for the download link, its fingerprint, and how to"
echo "            trust it (or safely click through the browser warning instead)."
echo "  managers: every manager session that has registered itself under a workspace"
echo "            root below; each writes its own registration on every wake."
echo "  stop:     Ctrl-C"
echo

cd "$ROOT"
exec uv run --extra app python -m app.serve \
    --host "$HOST" --port "$PORT" \
    ${PASS_THROUGH[@]+"${PASS_THROUGH[@]}"}
