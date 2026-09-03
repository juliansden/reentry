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

# Export values from the generated mission headers for the host-side resolver.
RUN printf '%s\n' \
        '#include <stdio.h>' \
        '#include "ci_lab_msgids.h"' \
        '#include "ci_lab_interface_cfg.h"' \
        '#include "to_lab_msgids.h"' \
        '#include "to_lab_interface_cfg.h"' \
        '#include "ci_lab_topicids.h"' \
        'int main(void) {' \
        '  printf("{\"CI_LAB_CMD_MID\": %u,\"CI_LAB_SEND_HK_MID\": %u,\"CI_LAB_HK_TLM_MID\": %u,\"CI_LAB_CMD_UDP_PORT\": %u,\"TO_LAB_CMD_MID\": %u,\"TO_LAB_TLM_PORT\": %u}\n", (unsigned)CI_LAB_CMD_MID, (unsigned)CI_LAB_SEND_HK_MID, (unsigned)CI_LAB_HK_TLM_MID, (unsigned)CI_LAB_MISSION_BASE_UDP_PORT, (unsigned)TO_LAB_CMD_MID, (unsigned)TO_LAB_MISSION_TLM_PORT);' \
        '  return 0;' \
        '}' > /tmp/ci_lab_ids.c \
        && cc -std=c99 -Werror \
            -I/src/cfs/sample_defs/inc \
            -I/src/cfs/build-native_std/inc \
            -I/src/cfs/build-native_std/native/default_cpu1/inc \
            -I/src/cfs/apps/ci_lab/fsw/inc \
            -I/src/cfs/apps/to_lab/fsw/inc \
            -I/src/cfs/cfe/modules/core_api/fsw/inc \
            -I/src/cfs/cfe/modules/config/fsw/inc \
            -I/src/cfs/cfe/modules/sb/fsw/inc \
            -I/src/cfs/osal/src/os/inc \
            -I/src/cfs/build-native_std/native/default_cpu1/osal/inc \
            -I/src/cfs/psp/fsw/inc \
            /tmp/ci_lab_ids.c -o /tmp/ci_lab_ids \
        && /tmp/ci_lab_ids > /src/cfs/build-native_std/native/ci_lab_ids.json

FROM ubuntu:22.04
COPY --from=build /src/cfs/build-native_std/exe/cpu1 /cfs/cpu1
# Generated headers, kept around so resolve_ids.py can extract the real (not guessed)
# MID/APID/port values baked in by this specific build.
COPY --from=build /src/cfs/build-native_std/native /cfs/generated_headers
WORKDIR /cfs/cpu1
# ci_lab's UDP command-ingest port per its sample_defs config (confirm against resolve_ids.py output).
EXPOSE 1234/udp
ENTRYPOINT ["./core-cpu1"]
