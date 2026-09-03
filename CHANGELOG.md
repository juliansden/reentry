# CHANGELOG


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
