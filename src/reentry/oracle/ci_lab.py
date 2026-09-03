"""ci_lab-aware oracle: reads NASA cFS ci_lab HK telemetry command counters.

Field offsets are pinned to the ci_lab v7.0.1 release housekeeping packet layout.
ci_lab increments a command-accept counter on success and a command-error counter
on a rejected/malformed command, letting this oracle distinguish clean rejection
from unexpected acceptance instead of just liveness.
"""

from __future__ import annotations

import struct

from reentry.generator.cases import PacketCase
from reentry.oracle.base import Oracle, Verdict
from reentry.transport.base import Transport

# Offsets within the ci_lab HK telemetry packet (v7.0.1).
# The 16-octet cFS telemetry header precedes the CI_LAB payload.
HK_USER_DATA_OFFSET = 16
CMD_ACCEPT_COUNTER_OFFSET = 0
CMD_ERROR_COUNTER_OFFSET = 1
INGEST_PACKETS_OFFSET = 4
INGEST_ERRORS_OFFSET = 8


def parse_command_counters(hk_packet: bytes) -> tuple[int, int]:
    """Extract (accept_count, error_count) from a raw ci_lab HK telemetry packet."""
    data = hk_packet[HK_USER_DATA_OFFSET:]
    if len(data) < 2:
        raise ValueError("HK payload too short to contain command counters")
    accept, error = struct.unpack_from(">BB", data, 0)
    return accept, error


def parse_ingest_counters(hk_packet: bytes) -> tuple[int, int]:
    """Extract (ingest_packet_count, ingest_error_count) from CI_LAB HK telemetry."""
    data = hk_packet[HK_USER_DATA_OFFSET:]
    if len(data) < INGEST_ERRORS_OFFSET + 4:
        raise ValueError("HK payload too short to contain ingest counters")
    packets = struct.unpack_from("<I", data, INGEST_PACKETS_OFFSET)[0]
    errors = struct.unpack_from("<I", data, INGEST_ERRORS_OFFSET)[0]
    return packets, errors


class CiLabOracle(Oracle):
    """Sends an HK request before and after each case and diffs the command counters."""

    def __init__(self, hk_request_payload_hex: str, probe_timeout: float = 2.0) -> None:
        self._hk_request_payload = bytes.fromhex(hk_request_payload_hex)
        self._probe_timeout = probe_timeout

    def _read_counters(self, transport: Transport) -> tuple[tuple[int, int], tuple[int, int]] | None:
        transport.send(self._hk_request_payload)
        reply = transport.receive(self._probe_timeout)
        if reply is None:
            return None
        return parse_command_counters(reply), parse_ingest_counters(reply)

    def judge(self, case: PacketCase, transport: Transport) -> tuple[Verdict, str]:
        before = self._read_counters(transport)
        if before is None:
            return Verdict.HANG, "no HK reply before sending case (target already unresponsive)"

        transport.send(case.packet_bytes)

        after = self._read_counters(transport)
        if after is None:
            return Verdict.HANG, "no HK reply after sending case (possible hang/crash)"

        accepted = after[0][0] != before[0][0]
        command_rejected = after[0][1] != before[0][1]
        ingest_rejected = after[1][1] != before[1][1]
        if accepted and case.expect_safe_reject:
            return Verdict.UNEXPECTED_ACCEPT, "command-accept counter incremented for a case expected to be rejected"
        if command_rejected:
            return Verdict.CLEAN_REJECT, "command-error counter incremented, target rejected the case"
        if ingest_rejected:
            return Verdict.SAFE_DROP, "ingest-error counter incremented, target safely dropped the packet"
        if accepted:
            return Verdict.CLEAN_REJECT, "command-accept counter incremented, matching the expected outcome"
        return Verdict.INCONCLUSIVE, "target alive but neither counter changed"
