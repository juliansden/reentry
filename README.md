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
python tests/fixtures/mock_target.py --port 1234 &
reentry run --config tests/fixtures/mock_target.toml --json report.json --junit report.xml
```

## CI

GitHub Actions runs the unit tests and mock-target pre-flight on pushes and pull requests. The cFS/ci_lab Docker validation is available through a manual workflow dispatch. Releases are driven by Conventional Commit messages on `main`.

- `fix:` creates a patch release
- `feat:` creates a minor release
- `BREAKING CHANGE:` creates a major release
