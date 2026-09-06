#!/usr/bin/env bash
#
# Run the Converge app beside this checkout. One command, nothing else to know.
#
#     scripts/run-app.sh
#
# It serves on http://127.0.0.1:8788, prints that URL, says how you sign in, and
# says where it looked for manager sessions. Ctrl-C stops it.
#
# Why a wrapper at all, when `uv run --extra app python -m app.serve` is one line
# already: that line has to be typed from the repository root, needs `--extra
# app` to be remembered, and says nothing about how to get in once it is up. A
# reader who has just started their first manager session should not have to
# know any of that. `composition.v1` Core 5 is the same idea for the install
# command; this is it for the app.
#
# Two flags, and both are decisions rather than conveniences:
#
#   --lan       bind every interface (0.0.0.0) instead of loopback, and print
#               the address a phone on the same network can open. Loopback is
#               the default on purpose: putting the page on the network is a
#               choice, and `app/README.md` says what the sign-in gate does and
#               does not promise there.
#   --port N    serve somewhere other than 8788. Use this when 8788 is already
#               taken -- by the service in `app/converge-app.service`, or by
#               another checkout.
#
# Anything else is handed to `app.serve` untouched (`--config`, `--state`).
set -euo pipefail

HOST=127.0.0.1
PORT=8788
LAN=0
PASS_THROUGH=()

usage() {
    cat <<'USAGE'
Run the Converge app beside this checkout.

    scripts/run-app.sh [--lan] [--port N] [-- ...args for app.serve]

  --lan       bind 0.0.0.0 (every interface) instead of 127.0.0.1, and print
              the address another device on this network can open
  --port N    serve on N instead of 8788
  -h, --help  this

Anything else is passed to `python -m app.serve` unchanged, so `--config PATH`
and `--state PATH` work as they do there. Ctrl-C stops the server.
USAGE
}

while [ $# -gt 0 ]; do
    case "$1" in
        --lan)
            LAN=1
            HOST=0.0.0.0
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
            # Deliberately not offered as a flag of its own: --lan is the
            # decision, and a bare --host invites binding an interface without
            # meaning to. Passed through so app.serve still answers for it.
            if [ $# -lt 2 ]; then
                echo "run-app.sh: --host needs an address" >&2
                exit 2
            fi
            HOST="$2"
            shift 2
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

if [ "$LAN" = "1" ]; then
    OPEN="http://$(hostname):${PORT}"
    ALSO="  also:     http://127.0.0.1:${PORT} (on this machine)"
else
    OPEN="http://127.0.0.1:${PORT}"
    ALSO="  network:  loopback only -- pass --lan to open it to this network"
fi

echo "Converge app -- from ${ROOT}"
echo "  open:     ${OPEN}"
echo "${ALSO}"
echo "  sign in:  your account on $(hostname) -- the username and password you log in"
echo "            with, checked by PAM. The app keeps no passwords."
echo "  managers: every manager session that has registered itself under a workspace"
echo "            root below; each writes its own registration on every wake."
echo "  stop:     Ctrl-C"
echo

cd "$ROOT"
exec uv run --extra app python -m app.serve \
    --host "$HOST" --port "$PORT" \
    ${PASS_THROUGH[@]+"${PASS_THROUGH[@]}"}
