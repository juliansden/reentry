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

cleanup() {
    docker rm -f "$container_name" >/dev/null 2>&1 || true
    rm -rf "$headers_dir" "$resolved_ids" "$config"
}
trap cleanup EXIT

if lsof -nP -iUDP:1234 >/dev/null 2>&1; then
    echo "UDP port 1234 is already in use; stop that process before starting cFS." >&2
    exit 1
fi

docker rm -f "$container_name" >/dev/null 2>&1 || true
docker build -t cfs-ci-lab docker/cfs_ci_lab
docker run -d \
    --name "$container_name" \
    --privileged \
    --sysctl fs.mqueue.msg_max=1024 \
    --add-host=host.docker.internal:host-gateway \
    -p 1234:1234/udp \
    cfs-ci-lab >/dev/null

docker cp "$container_name:/cfs/generated_headers" "$headers_dir"
"$python_bin" docker/cfs_ci_lab/resolve_ids.py "$headers_dir" "$resolved_ids"
"$python_bin" docker/cfs_ci_lab/render_config.py "$resolved_ids" "$config"

host_ip="$(docker exec "$container_name" getent ahostsv4 host.docker.internal | awk 'NR == 1 {print $1}')"
"$python_bin" docker/cfs_ci_lab/enable_to_lab.py "$resolved_ids" --destination-ip "$host_ip"

"$python_bin" -m reentry.cli run --config "$config" --json report.json --junit report.xml