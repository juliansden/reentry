#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
python_bin="${REENTRY_PYTHON:-$repo_root/.venv/bin/python}"
if [[ ! -x "$python_bin" ]]; then
    echo "Python environment not found at $python_bin; run: python3 -m venv .venv && .venv/bin/python -m pip install -e ." >&2
    exit 1
fi

container_name="${REENTRY_CONTAINER:-cfs-ci-lab}"
headers_dir="$(mktemp -d)"
resolved_ids="$(mktemp)"
config="$(mktemp)"
created_container=0

cleanup() {
    if [[ "$created_container" -eq 1 ]]; then
        docker rm -f "$container_name" >/dev/null 2>&1 || true
    fi
    rm -rf "$headers_dir" "$resolved_ids" "$config"
}
trap cleanup EXIT

if lsof -nP -iUDP:1234 >/dev/null 2>&1; then
    echo "UDP port 1234 is already in use; stop that process before starting cFS." >&2
    exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$container_name"; then
    echo "container '$container_name' already exists; remove it or set REENTRY_CONTAINER." >&2
    exit 1
fi

docker build -t cfs-ci-lab docker/cfs_ci_lab
docker run -d \
    --name "$container_name" \
    --privileged \
    --sysctl fs.mqueue.msg_max=1024 \
    --add-host=host.docker.internal:host-gateway \
    -p 127.0.0.1:1234:1234/udp \
    cfs-ci-lab >/dev/null
created_container=1

ready=0
for _ in $(seq 1 60); do
    if ! docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null | grep -q '^true$'; then
        echo "cFS container stopped before becoming operational." >&2
        exit 1
    fi
    logs="$(docker logs "$container_name" 2>&1)"
    if grep -q "CFE_ES_Main entering OPERATIONAL state" <<< "$logs"; then
        ready=1
        break
    fi
    sleep 1
done
if [[ "$ready" -ne 1 ]]; then
    echo "cFS did not finish booting in time." >&2
    exit 1
fi

docker cp "$container_name:/cfs/generated_headers" "$headers_dir"
"$python_bin" docker/cfs_ci_lab/resolve_ids.py "$headers_dir" "$resolved_ids"
"$python_bin" docker/cfs_ci_lab/render_config.py "$resolved_ids" "$config" --allowed-reply-host 127.0.0.1

host_ip="$(docker exec "$container_name" getent ahostsv4 host.docker.internal | awk 'NR == 1 {print $1}')"
"$python_bin" docker/cfs_ci_lab/enable_to_lab.py "$resolved_ids" --destination-ip "$host_ip"

if ! "$python_bin" - "$config" <<'PY'
import socket
import sys
import tomllib

from reentry.oracle.ci_lab import parse_command_counters

with open(sys.argv[1], "rb") as config_file:
    config = tomllib.load(config_file)
transport = config["transport"]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", transport["listen_port"]))
sock.settimeout(5.0)
sock.sendto(
    bytes.fromhex(transport["probe_payload_hex"]),
    (transport["host"], transport["port"]),
)
try:
    while True:
        reply, address = sock.recvfrom(65535)
        if (
            address[0] == transport["allowed_reply_host"]
            and len(reply) >= 6
            and int.from_bytes(reply[0:2], "big") & 0x07FF == transport["allowed_reply_apid"]
        ):
            parse_command_counters(reply)
            break
finally:
    sock.close()
PY
then
    echo "cFS did not return an HK telemetry reply after TO_LAB setup." >&2
    exit 1
fi

run_status=0
"$python_bin" -m reentry.cli run --config "$config" --json report.json --junit report.xml || run_status=$?

"$python_bin" - report.json <<'PY'
import json
import sys

with open(sys.argv[1]) as report_file:
    findings = json.load(report_file)["findings"]
known_good = [finding for finding in findings if finding["category"] == "known_good"]
if len(known_good) != 1 or known_good[0]["verdict"] != "clean_accept" or "CommandCounter increased" not in known_good[0]["detail"]:
    print("known-good CI_LAB NOOP did not produce a clean accept with a CommandCounter increase", file=sys.stderr)
    sys.exit(1)
print(known_good[0]["detail"])
PY

exit "$run_status"