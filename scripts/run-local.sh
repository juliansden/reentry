#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python_bin="${REENTRY_PYTHON:-$repo_root/.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
    echo "Python environment not found at $python_bin; run: python3 -m venv .venv && .venv/bin/python -m pip install -e ." >&2
    exit 1
fi

port="${REENTRY_PORT:-1234}"
if lsof -nP -iUDP:"$port" >/dev/null 2>&1; then
    echo "UDP port $port is already in use; stop that process or set REENTRY_PORT." >&2
    exit 1
fi

"$python_bin" tests/fixtures/mock_target.py --port "$port" &
target_pid=$!
config="$(mktemp)"
trap 'rm -f "$config"; kill "$target_pid" 2>/dev/null || true' EXIT
sed "s/port = 1234/port = $port/" tests/fixtures/mock_target.toml > "$config"

ready=0
for _ in $(seq 1 30); do
    if ! kill -0 "$target_pid" 2>/dev/null; then
        echo "mock target exited before becoming ready." >&2
        exit 1
    fi
    if TARGET_PORT="$port" "$python_bin" - <<'PY'
import os
import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.2)
sock.sendto(b"HK?", ("127.0.0.1", int(os.environ["TARGET_PORT"])))
try:
    sock.recvfrom(1024)
except TimeoutError:
    sys.exit(1)
sys.exit(0)
PY
    then
        ready=1
        break
    fi
    sleep 1
done
if [[ "$ready" -ne 1 ]]; then
    echo "mock target did not become ready in time." >&2
    exit 1
fi

"$python_bin" -m reentry.cli run --config "$config" --json report.json --junit report.xml