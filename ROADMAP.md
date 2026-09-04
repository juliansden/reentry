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

### Known Issues to Fix

- [ ] Record UDP delivery failures such as `EMSGSIZE` as transport evidence so an undelivered packet cannot be attributed to target behavior.
- [ ] Distinguish local socket or network failures from target `HANG` findings.
- [ ] Correlate or drain telemetry replies so stale packets cannot be used as a case's before/after evidence.
- [ ] Add an external health signal to distinguish `CRASH` from `HANG` when the target becomes unresponsive.
- [ ] Add target capabilities and evidence signals needed for `hardened-cfs` to enforce stricter expectations without making unsupported claims.
- [ ] Validate configuration values before execution, including hex payloads, ports, APIDs, timeouts, and case categories.
- [ ] Establish real-target baselines and automated or scheduled cFS regression coverage beyond manual workflow dispatch.
- [ ] Extend protocol coverage beyond the current primary-header and ci_lab command focus, including additional CCSDS behavior and transports.

### Planned Work

- [ ] Add target adapters and documented telemetry schemas
- [ ] Define profile-specific evidence requirements where targets expose the needed signals
- [ ] Add regression baselines and CI-friendly comparison tooling
- [ ] Extend CCSDS packet and transport coverage

## Phase 4: Advanced Robustness

- [ ] Integrate fuzzing with reproducible minimized cases
- [ ] Measure performance and sustained-load robustness
- [ ] Add CI platform integrations beyond GitHub Actions

Checked items have shipped and been validated in this repository. Unchecked
items are direction, not release commitments; update the checklist when a
milestone is merged and verified.