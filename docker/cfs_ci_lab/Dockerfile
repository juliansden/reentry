# Builds the real NASA cFS bundle (native_std) with ci_lab, pinned to v7.0.1.
# This is the ground-truth validation target — the mock in tests/fixtures/mock_target.py
# only proves the harness's pipeline works, not that ci_lab behaves any particular way.
FROM ubuntu:22.04 AS build

# Ubuntu package revisions change independently of the pinned cFS source release.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --branch v7.0.1 --depth 1 https://github.com/nasa/cFS.git cfs
WORKDIR /src/cfs
RUN git submodule update --init --depth 1

RUN make native_std.prep && make native_std.install

FROM ubuntu:22.04
COPY --from=build /src/cfs/build-native_std/exe/cpu1 /cfs/cpu1
# Generated headers, kept around so resolve_ids.py can extract the real (not guessed)
# MID/APID/port values baked in by this specific build.
COPY --from=build /src/cfs/build-native_std/native /cfs/generated_headers
WORKDIR /cfs/cpu1
# ci_lab's UDP command-ingest port per its sample_defs config (confirm against resolve_ids.py output).
EXPOSE 1234/udp
ENTRYPOINT ["./core-cpu1"]
