"""ci_lab-aware oracle: reads NASA cFS ci_lab HK telemetry command counters.

Field offsets are pinned to the ci_lab v7.0.1 release housekeeping packet layout.
ci_lab increments a command-accept counter on success and a command-error counter
on a rejected/malformed command, letting this oracle distinguish clean rejection
from unexpected acceptance instead of just liveness.
"""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass

from reentry.generator.cases import PacketCase
from reentry.oracle.base import Oracle, OracleResult, Verdict
from reentry.transport.base import Transport, TransportError

# Offsets within the ci_lab HK telemetry packet (v7.0.1).
# The 16-octet cFS telemetry header precedes the CI_LAB payload.
HK_USER_DATA_OFFSET = 16
CMD_ACCEPT_COUNTER_OFFSET = 0
CMD_ERROR_COUNTER_OFFSET = 1
INGEST_PACKETS_OFFSET = 4
INGEST_ERRORS_OFFSET = 8


@dataclass(frozen=True)
class CiLabCounters:
    command: int
    command_error: int
    enable_checksums: int
    socket_connected: int
    ingest_packets: int
    ingest_errors: int


def parse_hk_counters(hk_packet: bytes) -> CiLabCounters:
    """Extract all CI_LAB HK counters from a raw telemetry packet."""
    data = hk_packet[HK_USER_DATA_OFFSET:]
    if len(data) < INGEST_ERRORS_OFFSET + 4:
        raise ValueError("HK payload too short to contain CI_LAB counters")
    command, command_error, enable_checksums, socket_connected = struct.unpack_from(
        ">BBBB", data, 0
    )
    ingest_packets = struct.unpack_from("<I", data, INGEST_PACKETS_OFFSET)[0]
    ingest_errors = struct.unpack_from("<I", data, INGEST_ERRORS_OFFSET)[0]
    return CiLabCounters(
        command=command,
        command_error=command_error,
        enable_checksums=enable_checksums,
        socket_connected=socket_connected,
        ingest_packets=ingest_packets,
        ingest_errors=ingest_errors,
    )


def parse_command_counters(hk_packet: bytes) -> tuple[int, int]:
    """Extract (accept_count, error_count) from a raw ci_lab HK telemetry packet."""
    counters = parse_hk_counters(hk_packet)
    return counters.command, counters.command_error


def parse_ingest_counters(hk_packet: bytes) -> tuple[int, int]:
    """Extract (ingest_packet_count, ingest_error_count) from CI_LAB HK telemetry."""
    counters = parse_hk_counters(hk_packet)
    return counters.ingest_packets, counters.ingest_errors


class CiLabOracle(Oracle):
    """Sends an HK request before and after each case and diffs the command counters."""

    def __init__(self, hk_request_payload_hex: str, probe_timeout: float = 2.0) -> None:
        self._hk_request_payload = bytes.fromhex(hk_request_payload_hex)
        self._probe_timeout = probe_timeout

    def _read_counters(
        self, transport: Transport
    ) -> tuple[CiLabCounters | None, TransportError | None]:
        drain = getattr(transport, "drain_stale_replies", None)
        if drain is not None:
            drain()
        transport.send(self._hk_request_payload)
        transport_error = getattr(transport, "last_error", None)
        if transport_error is not None:
            return None, transport_error
        reply = transport.receive(self._probe_timeout)
        if reply is None:
            return None, getattr(transport, "last_error", None)
        return parse_hk_counters(reply), None

    def judge(self, case: PacketCase, transport: Transport) -> OracleResult:
        evidence = {"before": None, "after": None}
        before, transport_error = self._read_counters(transport)
        if before is None:
            if transport_error is not None:
                return OracleResult(
                    Verdict.INCONCLUSIVE,
                    "transport failed while reading HK counters before the case",
                    evidence,
                    transport_error,
                )
            return OracleResult(
                Verdict.HANG,
                "no HK reply before sending case (target already unresponsive)",
                evidence,
            )

        evidence["before"] = asdict(before)

        transport.send(case.packet_bytes)
        transport_error = getattr(transport, "last_error", None)
        if transport_error is not None:
            return OracleResult(
                Verdict.INCONCLUSIVE,
                "transport failed while sending the case",
                evidence,
                transport_error,
            )

        after, transport_error = self._read_counters(transport)
        if after is None:
            if transport_error is not None:
                return OracleResult(
                    Verdict.INCONCLUSIVE,
                    "transport failed while reading HK counters after the case",
                    evidence,
                    transport_error,
                )
            return OracleResult(
                Verdict.HANG,
                "no HK reply after sending case (possible hang/crash)",
                evidence,
            )

        evidence["after"] = asdict(after)

        accepted = after.command != before.command
        command_rejected = after.command_error != before.command_error
        ingest_rejected = after.ingest_errors != before.ingest_errors
        if accepted and case.expect_safe_reject:
            return OracleResult(
                Verdict.UNEXPECTED_ACCEPT,
                "command-accept counter incremented for a case expected to be rejected",
                evidence,
            )
        if command_rejected:
            return OracleResult(
                Verdict.CLEAN_REJECT,
                f"command-error counter incremented from {before.command_error} to {after.command_error}, "
                "target rejected the case",
                evidence,
            )
        if ingest_rejected:
            return OracleResult(
                Verdict.SAFE_DROP,
                f"ingest-error counter incremented from {before.ingest_errors} to {after.ingest_errors}, "
                "target safely dropped the packet",
                evidence,
            )
        if accepted:
            outcome = "known-good command accepted" if case.expect_accept else "command accepted"
            return OracleResult(
                Verdict.CLEAN_ACCEPT,
                f"CommandCounter increased from {before.command} to {after.command}, "
                f"target {outcome}",
                evidence,
            )
        if after.ingest_packets != before.ingest_packets:
            return OracleResult(
                Verdict.INCONCLUSIVE,
                f"target alive; IngestPackets changed from {before.ingest_packets} to "
                f"{after.ingest_packets} (delta includes the HK probe), but "
                "CommandCounter and CommandErrorCounter did not change",
                evidence,
            )
        return OracleResult(
            Verdict.INCONCLUSIVE,
            "target alive but IngestPackets, CommandCounter, CommandErrorCounter, and "
            "IngestErrors did not change",
            evidence,
        )
