# CHANGELOG


## v0.4.0 (2026-09-04)

### Bug Fixes

- Address PR review feedback
  ([`a3c4f20`](https://github.com/juliansden/reentry/commit/a3c4f20cb2f004e78af0fd8006f721e3bffa24bd))

Co-authored-by: juliansden <66048332+juliansden@users.noreply.github.com>

### Features

- Add reproducible target profiles
  ([`2b47eb3`](https://github.com/juliansden/reentry/commit/2b47eb3f0d4081cc64191c89246647c32cc471b6))

### Testing

- Tolerate styled CLI validation output
  ([`826691d`](https://github.com/juliansden/reentry/commit/826691dd830bee567a5b360bce8a62fb13f09b12))


## v0.3.0 (2026-09-04)

### Features

- Add CI lab known-good and malformed commands
  ([`029d37a`](https://github.com/juliansden/reentry/commit/029d37a5d55b5796ca83ebccc9f8585d259f3277))


## v0.2.0 (2026-09-03)

### Bug Fixes

- Make cFS verdicts observable
  ([`efb92e2`](https://github.com/juliansden/reentry/commit/efb92e2e57a9a5ab9828b601544599ebf63a6815))

### Features

- Distinguish safely dropped packets
  ([`86ffa2e`](https://github.com/juliansden/reentry/commit/86ffa2e2e17033ecee4703d43b3aa5a423a67674))


## v0.1.6 (2026-09-03)

### Bug Fixes

- Wait for cFS telemetry readiness
  ([`a9afcb5`](https://github.com/juliansden/reentry/commit/a9afcb56941a51f25184513ad0dfa02913fe2c30))

### Testing

- Support buggy local target mode
  ([`46e465c`](https://github.com/juliansden/reentry/commit/46e465ca008309f36e7c6e90073f815d21564d44))


## v0.1.5 (2026-09-03)

### Bug Fixes

- Address review feedback in run scripts
  ([`7069b1e`](https://github.com/juliansden/reentry/commit/7069b1e1dc0524539fe5ad106f22a8dcfe47f64b))

Co-authored-by: juliansden <66048332+juliansden@users.noreply.github.com>

### Chores

- Add local and Docker run scripts
  ([`311f720`](https://github.com/juliansden/reentry/commit/311f72048289968ea89247b0e276aa8ab66589e5))


## v0.1.4 (2026-09-03)

### Bug Fixes

- Align telemetry source docs and add expected-source UDP test
  ([`bd54fd6`](https://github.com/juliansden/reentry/commit/bd54fd6017055d393d8628358a1aa2dd43603e61))

Co-authored-by: juliansden <66048332+juliansden@users.noreply.github.com>

- Filter ci_lab telemetry replies by source
  ([`ab4514c`](https://github.com/juliansden/reentry/commit/ab4514c48282d8d1cfb3c8035a3196f3ea390555))

- Restrict ci_lab UDP command port to loopback
  ([`74cdd74`](https://github.com/juliansden/reentry/commit/74cdd74dacefb05ee4f91787f2f3f6c5ae68715b))


## v0.1.3 (2026-09-03)

### Bug Fixes

- Add reachable oversized test case
  ([`2e7a3f8`](https://github.com/juliansden/reentry/commit/2e7a3f87fdc56817b44b06fa3b70596c393f7036))

- Reject oversized commands in mock target's well-formed check
  ([`228948a`](https://github.com/juliansden/reentry/commit/228948acc7d3db33ea38a12b8f764aa65ec641ed))

The well-behaved mock never checked overall packet size, so the new 4KB oversized_reachable test
  case (structurally valid, no length lie) was accepted instead of rejected, causing an
  unexpected_accept finding in CI. Add a MAX_COMMAND_SIZE bound mirroring a real target's finite
  command buffer.


## v0.1.2 (2026-09-03)

### Bug Fixes

- Resolve Dockerfile lint warnings
  ([`ecc82cb`](https://github.com/juliansden/reentry/commit/ecc82cbbed0c953c1e148c4187d9e942c91d7946))

### Documentation

- Add project README and ignore local environments
  ([`ce2433a`](https://github.com/juliansden/reentry/commit/ce2433aff5f8991c9d842757524b49958a1a0a1c))


## v0.1.1 (2026-09-03)

### Bug Fixes

- Bump actions/checkout to v5 to clear Node 20 deprecation warning
  ([`9572b6d`](https://github.com/juliansden/reentry/commit/9572b6d830fb9ec17f4c775b9615618b2d833790))


## v0.1.0 (2026-09-03)

### Bug Fixes

- Python-semantic-release build_command must be a string not a bool
  ([`0c46401`](https://github.com/juliansden/reentry/commit/0c4640110e4bc9ce9a8937bc322cd0d055234312))

### Features

- Initial reentry CCSDS conformance/robustness harness
  ([`538cfcb`](https://github.com/juliansden/reentry/commit/538cfcbc2c03488b85baff3f4178e62d2722fc26))
