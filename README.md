# Reentry

Reentry is a Python harness for CCSDS Space Packet conformance and robustness testing. It builds and validates Space Packets, generates deterministic malformed and boundary-value inputs, delivers them over UDP, and reports whether a target rejects them safely or becomes unresponsive or unexpectedly accepts them.

## Status

The current implementation targets CCSDS Space Packets and provides:

- Primary-header packing, unpacking, and validation
- Deterministic boundary cases for malformed and degenerate packets
- A pluggable transport interface with a UDP adapter
- Liveness and ci_lab counter-based oracle implementations
- JSON and JUnit XML reports
- A CLI: `reentry run` and `reentry list-cases`
- A local mock target for fast development
- A Docker build for the cFS/ci_lab validation target

The cFS/ci_lab integration is a separate, heavier validation path. Its generated message IDs are resolved from the actual cFS build rather than guessed.

For a local cFS run, build and start the image with Docker Desktop, then use the
host-side helpers to resolve IDs, enable TO_LAB telemetry, and render the config:

```sh
docker build -t cfs-ci-lab docker/cfs_ci_lab
# Bind ci_lab's command port only on the host loopback interface.
docker run -d --name cfs-ci-lab --privileged --sysctl fs.mqueue.msg_max=1024 --add-host=host.docker.internal:host-gateway -p 127.0.0.1:1234:1234/udp cfs-ci-lab
docker cp cfs-ci-lab:/cfs/generated_headers /tmp/generated_headers
python docker/cfs_ci_lab/resolve_ids.py /tmp/generated_headers /tmp/resolved_ids.json
TELEMETRY_SOURCE=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' cfs-ci-lab)
python docker/cfs_ci_lab/render_config.py /tmp/resolved_ids.json /tmp/reentry.toml --allowed-reply-host "$TELEMETRY_SOURCE"
HOST_IP=$(docker exec cfs-ci-lab getent ahostsv4 host.docker.internal | awk 'NR == 1 {print $1}')
python docker/cfs_ci_lab/enable_to_lab.py /tmp/resolved_ids.json --destination-ip "$HOST_IP"
reentry run --config /tmp/reentry.toml --json report.json --junit report.xml
docker rm -f cfs-ci-lab
```

The destination address is discovered from Docker's host gateway, so the same
workflow works on Docker Desktop and Linux. The image exports the build-resolved
CI_LAB and TO_LAB values in `ci_lab_ids.json`, so IDs are never guessed.

## Development

Python 3.11 or newer is required.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

List the deterministic cases:

```sh
reentry list-cases
```

Run against the local mock target:

```sh
scripts/run-local.sh
```

The script stops the mock target when the run finishes. It uses UDP port `1234`;
set `REENTRY_PORT` if that port is busy:

```sh
REENTRY_PORT=1235 scripts/run-local.sh
```

Run the real cFS/ci_lab target in Docker with the complete setup and cleanup flow:

```sh
scripts/run-cfs-docker.sh
```

Docker must be running, and host UDP port `1234` must be available. The script
fails immediately if the port is busy, instead of continuing with a stopped
container and producing misleading hang findings. The first Docker build can
take a while because it compiles cFS; later builds use Docker's cache.

## CI

GitHub Actions runs the unit tests and mock-target pre-flight on pushes and pull requests. The cFS/ci_lab Docker validation is available through a manual workflow dispatch. Releases are driven by Conventional Commit messages on `main`.

- `fix:` creates a patch release
- `feat:` creates a minor release
- `BREAKING CHANGE:` creates a major release
