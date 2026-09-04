# Reentry Roadmap

Reentry is a reproducible CCSDS/UDP protocol robustness and security regression
harness for NASA cFS and similar targets.

## Phase 1: Harness Foundation

- [x] Deterministic CCSDS boundary and malformed packet generation
- [x] UDP delivery, liveness, and ci_lab telemetry-counter oracles
- [x] JSON and JUnit reports with per-case before/after telemetry evidence
- [x] Reproducible cFS/ci_lab Docker workflow using build-resolved identifiers

## Phase 2: Reproducible Target Profiles

- [x] `smoke` profile for the known-good command control and basic target liveness
- [x] `stock-cfs` profile to characterize a target as shipped without suppressing findings
- [x] `hardened-cfs` profile for stricter intended input handling
- [x] `full-robustness` profile for the complete malformed and boundary suite
- [x] Record the selected profile and telemetry evidence in reports
- [x] Preserve every verdict and structured telemetry evidence in JUnit output
- [x] Retain partial before/after telemetry evidence for post-case hangs
- [x] Archive JSON evidence from CI workflows
- [x] Cover profile, configuration, CLI, and report behavior with focused tests

All profiles retain the observed verdict and telemetry evidence. In particular,
an `INCONCLUSIVE` result is not presented as a rejection, and an
`UNEXPECTED_ACCEPT` remains a finding. The current ci_lab counter telemetry does
not support a stronger distinction between stock and hardened policy without
making an unsupported claim, so those profiles share the complete suite and
unsafe-verdict gate for now.

## Phase 3: Target Portability and Evidence

### P0: Verdict Integrity

- [ ] Replace swallowed UDP send errors with structured transport evidence, including errno, operation, packet size, and destination.
- [ ] Distinguish local socket or network failures from target `HANG` findings and define whether they produce a dedicated non-unsafe verdict or `INCONCLUSIVE` with a transport status.
- [ ] Correlate or drain telemetry replies before each request so stale packets cannot be used as a case's before/after evidence.
- [ ] Replace the mutable `oracle.last_evidence` side channel with a structured oracle result containing verdict, detail, evidence, and transport status.
- [ ] Add focused failure-path tests for `EMSGSIZE`, socket errors, timeouts, stale replies, and partial before/after evidence.

### P1: Configuration and Adapter Contracts

- [ ] Validate configuration values before execution, including hex payloads, ports, APIDs, timeouts, transport kinds, and case categories.
- [ ] Return actionable CLI errors for invalid TOML and Pydantic configuration instead of raw exceptions.
- [ ] Add target adapters and documented telemetry schemas.
- [ ] Define adapter capabilities, telemetry schema/version, required evidence fields, and verdict mapping.
- [ ] Add target capabilities and evidence signals needed for `hardened-cfs` to enforce stricter expectations without making unsupported claims.
- [ ] Define profile-specific evidence and verdict requirements where targets expose the needed signals.

### P2: Target Health and Regression Evidence

- [ ] Add an external health signal to distinguish `CRASH` from `HANG` when the target becomes unresponsive.
- [ ] Establish real-target baselines and automated or scheduled cFS regression coverage beyond manual workflow dispatch.
- [ ] Add report provenance: harness version, target build/version, resolved identifiers, configuration hash, adapter, and telemetry schema.
- [ ] Add regression baselines and CI-friendly comparison tooling.
- [ ] Replace fixed CI startup sleeps with readiness checks and fail the workflow when target boot readiness is not reached.

### P3: Protocol and Transport Expansion

- [ ] Extend protocol coverage beyond the current primary-header and ci_lab command focus, including additional CCSDS behavior and transports.
- [ ] Extend CCSDS packet and transport coverage

The `stock-cfs`, `hardened-cfs`, and `full-robustness` profiles currently share
the complete generated suite. Until target capabilities and stronger evidence
are available, `hardened-cfs` is a documented policy label rather than a stricter
enforcement mode.

### Required Test Coverage

- [ ] Test transport errors and confirm they cannot become unsafe target verdicts.
- [ ] Test invalid hex, port, APID, timeout, transport, and category configuration values.
- [ ] Test stale and delayed telemetry replies, including source and schema filtering.
- [ ] Test structured evidence preservation for before-only, after-only, and transport-failure cases.
- [ ] Test report provenance and baseline comparison behavior.

## Phase 4: Advanced Robustness

- [ ] Integrate fuzzing with reproducible minimized cases
- [ ] Measure performance and sustained-load robustness
- [ ] Add CI platform integrations beyond GitHub Actions

Checked items have shipped and been validated in this repository. Unchecked
items are direction, not release commitments; update the checklist when a
milestone is merged and verified.